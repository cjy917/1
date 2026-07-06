from functools import wraps

from flask import Flask, jsonify, request, send_file, send_from_directory, session
from flask_cors import CORS

from config import (
    AI_ASSISTANT_API_KEY,
    AI_ASSISTANT_BASE_URL,
    AI_ASSISTANT_ENABLED,
    AI_ASSISTANT_MAX_HISTORY,
    AI_ASSISTANT_MODEL,
    AI_ASSISTANT_TIMEOUT,
    DEFAULT_PAGE_SIZE,
    FRONTEND_DIST,
    MAX_PAGE_SIZE,
)
from models import Favorite, MovieComment, PlaybackCache, User, UserListItem, UserRating, Watchlist, db
from services.ai_rag_service import run_full_rag_pipeline
from services.analytics_service import (
    actor_distribution,
    analytics_filter_options,
    award_distribution,
    country_distribution,
    country_genre_correlation,
    director_distribution,
    duration_distribution,
    featured_movies,
    genre_distribution,
    get_all_movies,
    language_distribution,
    monthly_release_distribution,
    overview_stats,
    rating_distribution,
    rating_duration_correlation,
    rating_leaderboard,
    review_count_distribution,
    source_distribution,
    top_movies,
    wordcloud_data,
    year_distribution,
)
from services.poster_theme_service import get_movie_hero_theme
from services.movie_service import (
    get_filter_options,
    get_home_sections,
    get_movie_by_id,
    get_movies_by_award,
    get_similar_movies,
    list_movies,
    parse_crawled_reviews,
    poster_color,
    resolve_poster_file,
    search_suggest,
)
from services.chart_service import (
    get_filmmaker_detail,
    get_filmmaker_overview,
)
from services.recommendation_service import (
    get_cold_start_movies,
    get_content_similar_movies,
    hybrid_recommendations,
    refresh_spark_recommendations,
)
from services.spark_vm_client import SparkVMError
from services.ratings_service import export_spark_history_ratings_file, seed_crawled_ratings
from services.trailer_service import _trailer_memory_cache, get_local_trailer_path, list_local_trailer_ids, resolve_trailer
from services.video_service import (
    get_local_video_path,
    pick_remote_url,
    proxy_video_stream,
    resolve_playback,
)


def _migrate_playback_cache() -> None:
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    if "playback_cache" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("playback_cache")}
    if "tmdb_id" not in columns:
        db.session.execute(text("ALTER TABLE playback_cache ADD COLUMN tmdb_id VARCHAR(32)"))
    PlaybackCache.query.filter(
        (PlaybackCache.trailer_key == "demo") | (PlaybackCache.trailer_type == "none")
    ).delete(synchronize_session=False)
    db.session.commit()


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object("config")
    CORS(app, supports_credentials=True, origins=["http://localhost:5173", "http://127.0.0.1:5173"])
    db.init_app(app)

    with app.app_context():
        db.create_all()
        try:
            _migrate_playback_cache()
        except Exception as exc:
            print(f"playback_cache migrate skipped: {exc}")

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                return jsonify({"error": "请先登录"}), 401
            return view(*args, **kwargs)

        return wrapped

    def _collect_linked_entities_from_rag(rag) -> list:
        if not rag:
            return []
        entities = []
        seen_ids = set()
        rag_matches = getattr(rag, "matched_movies", None) or []
        for m in rag_matches:
            mid = None
            if isinstance(m, dict):
                mid = m.get("id") or m.get("movie_id")
                title = m.get("title") or m.get("name") or ""
            else:
                mid = getattr(m, "id", None) or getattr(m, "movie_id", None)
                title = getattr(m, "title", None) or getattr(m, "name", None) or ""
            if mid and str(mid) not in seen_ids:
                seen_ids.add(str(mid))
                entities.append({"type": "movie", "name": str(title), "id": str(mid)})
            elif title and title not in [e.get("name") for e in entities]:
                entities.append({"type": "movie", "name": str(title), "id": None})
        return entities

    def _extract_movie_linked_entities_from_reply(reply_text: str, fallback_rag=None) -> list:
        import re
        entities = _collect_linked_entities_from_rag(fallback_rag)
        seen = {(e.get("name"), e.get("id")) for e in entities}
        pattern = re.compile(r"[《〈]([^》〉]{1,50})[》〉]")
        titles = pattern.findall(reply_text or "")
        for title in titles:
            title = title.strip()
            if not title:
                continue
            hit = None
            try:
                suggest = search_suggest(title, limit=3)
                if isinstance(suggest, list):
                    for s in suggest:
                        s_title = s.get("title") if isinstance(s, dict) else None
                        if s_title == title:
                            hit = s
                            break
                    if not hit and suggest:
                        hit = suggest[0]
            except Exception as e:
                print(f"[AI] search_suggest failed for 「{title}」: {e}")
            mid = hit.get("id") if isinstance(hit, dict) else None
            key = (title, str(mid) if mid else None)
            if key in seen:
                continue
            seen.add(key)
            entities.append({"type": "movie", "name": title, "id": str(mid) if mid else None})
        return entities

    def _classify_ai_error(err_info, data) -> str:
        if err_info and isinstance(err_info, dict):
            code = err_info.get("code") or err_info.get("status_code") or 0
            msg = (err_info.get("message") or err_info.get("error") or "").lower()
            if isinstance(code, int):
                if code >= 500:
                    return "upstream_5xx"
                if code == 401 or code == 403:
                    return "auth_4xx"
                if code == 404:
                    return "upstream_404"
                if code >= 400:
                    return "upstream_4xx"
            if "timeout" in msg or "timed out" in msg:
                return "backend_504"
            if "connection" in msg or "refused" in msg or "network" in msg:
                return "backend_502"
        if not data:
            return "backend_502"
        return "backend_500"

    def _ai_error_hint(category: str) -> str:
        mapping = {
            "upstream_5xx": "上游AI服务暂时不可用，请稍后再试。",
            "upstream_404": "请求的模型接口不存在，请检查配置的BASE_URL。",
            "auth_4xx": "API Key无效或已过期，请检查secrets.local中的配置。",
            "upstream_4xx": "请求参数不合法，请稍后再试。",
            "backend_502": "无法连接到上游AI服务，请检查网络连接或代理设置。",
            "backend_504": "上游AI服务响应超时，请稍后再试。",
            "backend_500": "AI服务发生内部错误，请稍后再试。",
            "backend_503": "AI功能暂未启用或未配置完整。",
        }
        return mapping.get(category, "AI服务暂时不可用，请稍后再试。")

    def _build_ai_debug_extras(err_info) -> list:
        suggestions = []
        if err_info and isinstance(err_info, dict):
            code = err_info.get("code") or err_info.get("status_code")
            msg = (err_info.get("message") or err_info.get("error") or "").lower()
            if code in (401, 403) or "unauthorized" in msg or "invalid" in msg:
                suggestions.append("检查 secrets.local 中 AI_ASSISTANT_API_KEY 是否正确")
                suggestions.append("前往 https://cloud.siliconflow.cn/ 确认API Key有效且未过期")
            if "timeout" in msg or "timed out" in msg:
                suggestions.append("检查网络连接是否通畅")
                suggestions.append("在 config.py 中调大 AI_ASSISTANT_TIMEOUT")
            if "connection" in msg or "refused" in msg:
                suggestions.append("检查 AI_ASSISTANT_BASE_URL 是否正确")
                suggestions.append("确认是否需要配置 HTTP_PROXY 代理（Mac需注释EXTERNAL_HTTP_PROXY）")
        return suggestions

    @app.route("/api/health")
    def health():
        stats = overview_stats(user_count=User.query.count(), rating_count=UserRating.query.count())
        return jsonify({"status": "ok", **stats})

    @app.route("/api/auth/register", methods=["POST"])
    def register():
        payload = request.get_json(force=True)
        username = (payload.get("username") or "").strip()
        email = (payload.get("email") or "").strip()
        password = payload.get("password") or ""
        if not username or not email or len(password) < 6:
            return jsonify({"error": "用户名、邮箱不能为空，密码至少6位"}), 400
        if User.query.filter((User.username == username) | (User.email == email)).first():
            return jsonify({"error": "用户名或邮箱已存在"}), 400
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        session["user_id"] = user.id
        return jsonify({"message": "注册成功", "user": user.to_dict()})

    @app.route("/api/auth/login", methods=["POST"])
    def login():
        payload = request.get_json(force=True)
        username = (payload.get("username") or "").strip()
        password = payload.get("password") or ""
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            return jsonify({"error": "用户名或密码错误"}), 401
        session["user_id"] = user.id
        return jsonify({"message": "登录成功", "user": user.to_dict()})

    @app.route("/api/auth/logout", methods=["POST"])
    def logout():
        session.pop("user_id", None)
        return jsonify({"message": "已退出登录"})

    @app.route("/api/auth/me")
    def me():
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"user": None})
        user = db.session.get(User, user_id)
        return jsonify({"user": user.to_dict() if user else None})

    @app.route("/api/movies")
    def movies():
        page = max(int(request.args.get("page", 1)), 1)
        page_size = min(int(request.args.get("page_size", DEFAULT_PAGE_SIZE)), MAX_PAGE_SIZE)
        genre = request.args.get("genre")
        genres_param = request.args.get("genres")
        genres = [g.strip() for g in genres_param.split(",") if g.strip()] if genres_param else None
        languages_param = request.args.get("languages")
        languages = [lang.strip() for lang in languages_param.split(",") if lang.strip()] if languages_param else None
        year = request.args.get("year")
        year_from = request.args.get("year_from")
        year_to = request.args.get("year_to")
        keyword = request.args.get("keyword") or request.args.get("q")
        director = request.args.get("director")
        actor = request.args.get("actor")
        sort = request.args.get("sort", "rating_desc")
        min_rating = request.args.get("min_rating")
        max_rating = request.args.get("max_rating")
        min_votes = request.args.get("min_votes")
        data = list_movies(
            page=page,
            page_size=page_size,
            genre=genre,
            genres=genres,
            languages=languages,
            year=int(year) if year else None,
            year_from=int(year_from) if year_from else None,
            year_to=int(year_to) if year_to else None,
            min_rating=float(min_rating) if min_rating else None,
            max_rating=float(max_rating) if max_rating else None,
            min_votes=int(min_votes) if min_votes else None,
            keyword=keyword,
            director=director,
            actor=actor,
            sort=sort,
        )
        return jsonify(data)

    # ---------- 影人板块 API ----------
    @app.route("/api/charts/filmmakers")
    def charts_filmmakers():
        """影人列表页：导演榜 + 演员榜（ChartsView）。"""
        director_limit = min(int(request.args.get("director_limit", 24)), 40)
        actor_limit = min(int(request.args.get("actor_limit", 24)), 40)
        return jsonify(get_filmmaker_overview(director_limit, actor_limit))

    @app.route("/api/charts/filmmaker/<role>/<path:name>")
    def charts_filmmaker_detail(role: str, name: str):
        """影人详情页：作品列表 + 相关影人（FilmmakerDetailView）。"""
        if role not in ("director", "actor"):
            return jsonify({"error": "role 需为 director 或 actor"}), 400
        limit_arg = request.args.get("limit")
        limit = min(int(limit_arg), 500) if limit_arg else None
        detail = get_filmmaker_detail(name, role, limit=limit)
        if not detail:
            return jsonify({"error": "未找到该影人相关电影"}), 404
        return jsonify(detail)

    @app.route("/api/movies/home")
    def home_sections():
        return jsonify(get_home_sections())

    @app.route("/api/movies/filters")
    def movie_filters():
        return jsonify(get_filter_options())

    @app.route("/api/movies/search")
    def movie_search():
        keyword = request.args.get("q", "")
        return jsonify({"items": search_suggest(keyword)})

    @app.route("/api/movies/awards")
    def movie_awards():
        award_type = request.args.get("award_type", "oscars")
        page = max(1, int(request.args.get("page", 1)))
        page_size = min(50, int(request.args.get("page_size", 20)))
        year_param = request.args.get("year")
        year = int(year_param) if year_param else None
        return jsonify(get_movies_by_award(award_type, page, page_size, year))

    @app.route("/api/movies/<int:movie_id>")
    def movie_detail(movie_id: int):
        movie = get_movie_by_id(movie_id)
        if not movie:
            return jsonify({"error": "电影不存在"}), 404
        movie["crawled_review_list"] = parse_crawled_reviews(movie.get("reviews"))
        user_id = session.get("user_id")
        if user_id:
            rating = UserRating.query.filter_by(user_id=user_id, movie_id=movie_id).first()
            favorite = Favorite.query.filter_by(user_id=user_id, movie_id=movie_id).first()
            watchlist = Watchlist.query.filter_by(user_id=user_id, movie_id=movie_id).first()
            list_item = UserListItem.query.filter_by(user_id=user_id, movie_id=movie_id).first()
            movie["my_rating"] = rating.score if rating else None
            movie["is_favorite"] = favorite is not None
            movie["is_watchlist"] = watchlist is not None
            movie["in_list"] = list_item is not None
        else:
            movie["my_rating"] = None
            movie["is_favorite"] = False
            movie["is_watchlist"] = False
            movie["in_list"] = False
        movie["hero_theme"] = get_movie_hero_theme(movie_id, movie.get("cover_path"))
        return jsonify(movie)

    @app.route("/api/movies/<int:movie_id>/similar")
    def similar_movies(movie_id: int):
        return jsonify({"items": get_similar_movies(movie_id)})

    @app.route("/api/movies/<int:movie_id>/trailer")
    def movie_trailer(movie_id: int):
        movie = get_movie_by_id(movie_id)
        if not movie:
            return jsonify({"error": "电影不存在"}), 404
        if request.args.get("refresh") == "1":
            _trailer_memory_cache.pop(movie_id, None)
            cache = db.session.get(PlaybackCache, movie_id)
            if cache:
                cache.trailer_type = None
                cache.trailer_key = None
                cache.tmdb_id = None
                db.session.commit()
        autoplay = request.args.get("autoplay", "0") == "1"
        return jsonify(resolve_trailer(movie, autoplay=autoplay))

    @app.route("/api/movies/<int:movie_id>/play")
    def movie_playback(movie_id: int):
        movie = get_movie_by_id(movie_id)
        if not movie:
            return jsonify({"error": "电影不存在"}), 404
        quality = request.args.get("quality", "auto")
        search_archive = request.args.get("search_archive", "1") != "0"
        return jsonify(resolve_playback(movie, quality=quality, search_archive=search_archive))

    @app.route("/api/videos/<int:movie_id>")
    def stream_video(movie_id: int):
        quality = request.args.get("quality", "auto")
        local_path = get_local_video_path(str(movie_id), quality)
        if local_path:
            mime = {
                ".mp4": "video/mp4",
                ".webm": "video/webm",
                ".mkv": "video/x-matroska",
                ".m4v": "video/mp4",
            }.get(local_path.suffix.lower(), "video/mp4")
            return send_from_directory(
                local_path.parent,
                local_path.name,
                mimetype=mime,
                conditional=True,
            )
        remote = pick_remote_url(movie_id)
        if remote:
            return proxy_video_stream(remote, request.headers.get("Range"))
        return jsonify({"error": "正片视频不存在"}), 404

    @app.route("/api/trailers/<int:movie_id>")
    def stream_trailer(movie_id: int):
        local_path = get_local_trailer_path(movie_id)
        if local_path:
            mime = {
                ".mp4": "video/mp4",
                ".webm": "video/webm",
                ".m4v": "video/mp4",
            }.get(local_path.suffix.lower(), "video/mp4")
            return send_from_directory(
                local_path.parent,
                local_path.name,
                mimetype=mime,
                conditional=True,
            )
        return jsonify({"error": "预告片不存在"}), 404

    @app.route("/api/trailers/local-ids")
    def local_trailer_ids():
        return jsonify({"ids": list_local_trailer_ids()})

    @app.route("/api/posters/<int:movie_id>")
    def poster(movie_id: int):
        movie = get_movie_by_id(movie_id)
        title = movie["title"] if movie else str(movie_id)
        cover = movie.get("cover_path") if movie else None
        thumb_width = request.args.get("w", type=int)
        if thumb_width:
            from services.poster_thumb_service import try_send_poster_thumb

            thumb_response = try_send_poster_thumb(movie_id, cover, thumb_width)
            if thumb_response is not None:
                return thumb_response
        file_path = resolve_poster_file(movie_id, cover)
        if file_path:
            response = send_file(file_path)
            response.headers["Cache-Control"] = "public, max-age=86400"
            return response
        color = poster_color(title)
        svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='500' height='750' viewBox='0 0 500 750'>
            <defs>
              <linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>
                <stop offset='0%' stop-color='#042541'/>
                <stop offset='100%' stop-color='{color}'/>
              </linearGradient>
            </defs>
            <rect width='500' height='750' fill='url(#g)'/>
            <text x='50%' y='48%' fill='#ffffff' font-size='42' font-family='Arial' text-anchor='middle'>{title[:8]}</text>
            <text x='50%' y='56%' fill='#01B4E4' font-size='24' font-family='Arial' text-anchor='middle'>FYWZ movies</text>
        </svg>"""
        return svg, 200, {"Content-Type": "image/svg+xml; charset=utf-8"}

    @app.route("/api/ratings", methods=["POST", "DELETE"])
    @login_required
    def rate_movie():
        user_id = session["user_id"]
        if request.method == "DELETE":
            movie_id = int(request.args.get("movie_id", 0))
            if not movie_id:
                return jsonify({"error": "缺少 movie_id"}), 400
            rating = UserRating.query.filter_by(user_id=user_id, movie_id=movie_id).first()
            if not rating:
                return jsonify({"error": "尚未评分"}), 404
            db.session.delete(rating)
            db.session.commit()
            return jsonify({"message": "评分已删除"})

        payload = request.get_json(force=True)
        movie_id = int(payload.get("movie_id"))
        score = float(payload.get("score", 0))
        if score < 0.5 or score > 10:
            return jsonify({"error": "评分需在 0.5-10 之间"}), 400
        if not get_movie_by_id(movie_id):
            return jsonify({"error": "电影不存在"}), 404
        rating = UserRating.query.filter_by(user_id=user_id, movie_id=movie_id).first()
        if rating:
            rating.score = score
        else:
            rating = UserRating(user_id=user_id, movie_id=movie_id, score=score)
            db.session.add(rating)
        db.session.commit()
        return jsonify({"message": "评分成功", "rating": rating.to_dict()})

    @app.route("/api/favorites", methods=["GET", "POST", "DELETE"])
    @login_required
    def favorites():
        user_id = session["user_id"]
        if request.method == "GET":
            rows = Favorite.query.filter_by(user_id=user_id).order_by(Favorite.created_at.desc()).all()
            movie_ids = [row.movie_id for row in rows]
            from services.movie_service import get_movies_by_ids

            movies = get_movies_by_ids(movie_ids)
            return jsonify({"items": movies})
        if request.method == "POST":
            movie_id = int((request.get_json(force=True) or {}).get("movie_id"))
            if Favorite.query.filter_by(user_id=user_id, movie_id=movie_id).first():
                return jsonify({"message": "已在收藏夹"})
            db.session.add(Favorite(user_id=user_id, movie_id=movie_id))
            db.session.commit()
            return jsonify({"message": "收藏成功"})
        movie_id = int(request.args.get("movie_id"))
        Favorite.query.filter_by(user_id=user_id, movie_id=movie_id).delete()
        db.session.commit()
        return jsonify({"message": "已取消收藏"})

    @app.route("/api/watchlist", methods=["GET", "POST", "DELETE"])
    @login_required
    def watchlist():
        user_id = session["user_id"]
        if request.method == "GET":
            rows = Watchlist.query.filter_by(user_id=user_id).order_by(Watchlist.created_at.desc()).all()
            from services.movie_service import get_movies_by_ids

            return jsonify({"items": get_movies_by_ids([row.movie_id for row in rows])})
        if request.method == "POST":
            movie_id = int((request.get_json(force=True) or {}).get("movie_id"))
            if Watchlist.query.filter_by(user_id=user_id, movie_id=movie_id).first():
                return jsonify({"message": "已在待看片单"})
            db.session.add(Watchlist(user_id=user_id, movie_id=movie_id))
            db.session.commit()
            return jsonify({"message": "已添加到待看片单"})
        movie_id = int(request.args.get("movie_id"))
        Watchlist.query.filter_by(user_id=user_id, movie_id=movie_id).delete()
        db.session.commit()
        return jsonify({"message": "已从待看片单移除"})

    @app.route("/api/lists", methods=["GET", "POST", "DELETE"])
    @login_required
    def user_lists():
        user_id = session["user_id"]
        if request.method == "GET":
            rows = UserListItem.query.filter_by(user_id=user_id).order_by(UserListItem.created_at.desc()).all()
            from services.movie_service import get_movies_by_ids

            return jsonify({"items": get_movies_by_ids([row.movie_id for row in rows])})
        if request.method == "POST":
            movie_id = int((request.get_json(force=True) or {}).get("movie_id"))
            if UserListItem.query.filter_by(user_id=user_id, movie_id=movie_id).first():
                return jsonify({"message": "已在片单中"})
            db.session.add(UserListItem(user_id=user_id, movie_id=movie_id))
            db.session.commit()
            return jsonify({"message": "已添加到片单"})
        movie_id = int(request.args.get("movie_id"))
        UserListItem.query.filter_by(user_id=user_id, movie_id=movie_id).delete()
        db.session.commit()
        return jsonify({"message": "已从片单移除"})

    @app.route("/api/movies/<int:movie_id>/comments", methods=["GET"])
    def movie_comments(movie_id: int):
        if not get_movie_by_id(movie_id):
            return jsonify({"error": "电影不存在"}), 404
        rows = (
            MovieComment.query.filter_by(movie_id=movie_id)
            .order_by(MovieComment.created_at.desc())
            .all()
        )
        user_ids = {row.user_id for row in rows}
        users = {u.id: u.username for u in User.query.filter(User.id.in_(user_ids)).all()} if user_ids else {}
        current_user_id = session.get("user_id")
        items = []
        for row in rows:
            item = row.to_dict(username=users.get(row.user_id, "用户"))
            item["is_mine"] = current_user_id == row.user_id
            items.append(item)
        return jsonify({"items": items})

    @app.route("/api/comments", methods=["POST", "DELETE"])
    @login_required
    def comments():
        user_id = session["user_id"]
        if request.method == "DELETE":
            movie_id = int(request.args.get("movie_id", 0))
            if not movie_id:
                return jsonify({"error": "缺少 movie_id"}), 400
            row = MovieComment.query.filter_by(user_id=user_id, movie_id=movie_id).first()
            if not row:
                return jsonify({"error": "评论不存在"}), 404
            db.session.delete(row)
            db.session.commit()
            return jsonify({"message": "评论已删除"})

        payload = request.get_json(force=True) or {}
        movie_id = int(payload.get("movie_id", 0))
        content = (payload.get("content") or "").strip()
        score = payload.get("score")
        if not movie_id:
            return jsonify({"error": "缺少 movie_id"}), 400
        if not get_movie_by_id(movie_id):
            return jsonify({"error": "电影不存在"}), 404
        if len(content) < 5:
            return jsonify({"error": "评论至少 5 个字"}), 400
        if len(content) > 2000:
            return jsonify({"error": "评论不能超过 2000 字"}), 400
        parsed_score = None
        if score is not None and score != "":
            parsed_score = float(score)
            if parsed_score < 0.5 or parsed_score > 10:
                return jsonify({"error": "评分需在 0.5-10 之间"}), 400

        row = MovieComment.query.filter_by(user_id=user_id, movie_id=movie_id).first()
        if row:
            row.content = content
            row.score = parsed_score
        else:
            row = MovieComment(user_id=user_id, movie_id=movie_id, content=content, score=parsed_score)
            db.session.add(row)

        if parsed_score is not None:
            rating = UserRating.query.filter_by(user_id=user_id, movie_id=movie_id).first()
            if rating:
                rating.score = parsed_score
            else:
                db.session.add(UserRating(user_id=user_id, movie_id=movie_id, score=parsed_score))

        db.session.commit()

        user = User.query.get(user_id)
        item = row.to_dict(username=user.username if user else "用户")
        item["is_mine"] = True
        return jsonify({"message": "评论发表成功", "item": item})

    @app.route("/api/user/ratings")
    @login_required
    def my_ratings():
        user_id = session["user_id"]
        rows = UserRating.query.filter_by(user_id=user_id).order_by(UserRating.updated_at.desc()).all()
        movie_ids = [row.movie_id for row in rows]
        from services.movie_service import get_movies_by_ids

        movie_map = {m["movie_id"]: m for m in get_movies_by_ids(movie_ids)}
        items = []
        for row in rows:
            movie = movie_map.get(row.movie_id)
            if movie:
                items.append({**movie, "my_rating": row.score})
        return jsonify({"items": items})

    def analytics_filters():
        return {
            "genre": request.args.get("genre"),
            "year": request.args.get("year"),
            "country": request.args.get("country"),
        }

    @app.route("/api/analytics/filter-options")
    def analytics_filter_options_route():
        genre_limit = min(int(request.args.get("genre_limit", 25)), 50)
        country_limit = min(int(request.args.get("country_limit", 20)), 30)
        year_from = int(request.args.get("year_from", 2010))
        return jsonify(analytics_filter_options(genre_limit, country_limit, year_from))

    @app.route("/api/analytics/overview")
    def analytics_overview():
        return jsonify(
            overview_stats(
                **analytics_filters(),
                user_count=User.query.count(),
                rating_count=UserRating.query.count(),
            )
        )

    @app.route("/api/analytics/genres")
    def analytics_genres():
        limit = min(int(request.args.get("limit", 15)), 50)
        return jsonify(genre_distribution(limit=limit, **analytics_filters()))

    @app.route("/api/analytics/years")
    def analytics_years():
        return jsonify(year_distribution(**analytics_filters()))

    @app.route("/api/analytics/countries")
    def analytics_countries():
        limit = min(int(request.args.get("limit", 12)), 50)
        return jsonify(country_distribution(limit=limit, **analytics_filters()))

    @app.route("/api/analytics/ratings")
    def analytics_ratings():
        return jsonify(rating_distribution(**analytics_filters()))

    @app.route("/api/analytics/rating-leaderboard")
    def analytics_rating_leaderboard():
        limit = min(int(request.args.get("limit", 10)), 20)
        return jsonify({"items": rating_leaderboard(limit=limit)})

    @app.route("/api/analytics/actors")
    def analytics_actors():
        limit = min(int(request.args.get("limit", 10)), 50)
        return jsonify(actor_distribution(limit=limit, **analytics_filters()))

    @app.route("/api/analytics/top")
    def analytics_top():
        limit = min(int(request.args.get("limit", 12)), 50)
        return jsonify(top_movies(limit=limit, **analytics_filters()))

    @app.route("/api/analytics/featured")
    def analytics_featured():
        limit = min(int(request.args.get("limit", 12)), 50)
        return jsonify(featured_movies(limit=limit, **analytics_filters()))

    @app.route("/api/analytics/movies")
    def analytics_movies():
        limit = min(int(request.args.get("limit", 500)), 1000)
        return jsonify(get_all_movies(limit=limit, **analytics_filters()))

    @app.route("/api/analytics/languages")
    def analytics_languages():
        limit = min(int(request.args.get("limit", 10)), 50)
        return jsonify(language_distribution(limit=limit, **analytics_filters()))

    @app.route("/api/analytics/duration")
    def analytics_duration():
        return jsonify(duration_distribution(**analytics_filters()))

    @app.route("/api/analytics/directors")
    def analytics_directors():
        limit = min(int(request.args.get("limit", 10)), 50)
        return jsonify(director_distribution(limit=limit, **analytics_filters()))

    @app.route("/api/analytics/reviews")
    def analytics_reviews():
        return jsonify(review_count_distribution(**analytics_filters()))

    @app.route("/api/analytics/country-genre")
    def analytics_country_genre():
        limit = min(int(request.args.get("limit", 8)), 50)
        return jsonify(country_genre_correlation(limit=limit, **analytics_filters()))

    @app.route("/api/analytics/rating-duration")
    def analytics_rating_duration():
        return jsonify(rating_duration_correlation(**analytics_filters()))

    @app.route("/api/analytics/awards")
    def analytics_awards():
        limit = min(int(request.args.get("limit", 10)), 50)
        return jsonify(award_distribution(limit=limit, **analytics_filters()))

    @app.route("/api/analytics/monthly")
    def analytics_monthly():
        return jsonify(monthly_release_distribution(**analytics_filters()))

    @app.route("/api/analytics/wordcloud")
    def analytics_wordcloud():
        limit = min(int(request.args.get("limit", 60)), 120)
        return jsonify(wordcloud_data(limit=limit, **analytics_filters()))

    @app.route("/api/analytics/sources")
    def analytics_sources():
        return jsonify({"items": source_distribution()})

    # ---------- 智能推荐 API ----------
    @app.route("/api/recommend/personal")
    @login_required
    def personal_recommend():
        """已登录用户进入推荐页时拉取个性化/冷启动推荐（RecommendView load）。"""
        user_id = session["user_id"]
        return jsonify(hybrid_recommendations(user_id))

    @app.route("/api/recommend/refresh", methods=["POST"])
    @login_required
    def refresh_recommend():
        """用户点击「刷新推荐」：导出评分 → VM Spark 增量计算 → 返回新结果。"""
        user_id = session["user_id"]
        try:
            return jsonify(refresh_spark_recommendations(user_id))
        except SparkVMError as exc:
            return jsonify({"error": str(exc)}), 503

    @app.route("/api/recommend/similar/<int:movie_id>")
    def graph_similar(movie_id: int):
        return jsonify(
            {
                "items": get_content_similar_movies(movie_id),
                "algorithm": "content_tfidf",
            }
        )

    @app.route("/api/recommend/guest")
    def guest_recommend():
        """未登录访客推荐页：只返回热门电影（冷启动）。"""
        popular = get_cold_start_movies(20)
        return jsonify(
            {
                "items": popular,
                "hybrid_items": [],
                "als_items": [],
                "graphx_items": [],
                "content_items": [],
                "popular_items": popular,
                "strategy": "cold_start",
                "strategy_label": "冷启动 · 与首页「热门电影」相同",
                "source": "fallback",
                "rating_count": 0,
                "spark_imported": False,
                "personalized_ready": False,
                "rating_required": 3,
            }
        )

    # ---------- AI 智能语音助手 API ----------
    @app.route("/api/ai/config")
    def ai_assistant_config():
        """前端 AIVoiceAssistant 初始化时调用：返回是否启用、是否有 Key、模型名。"""
        return jsonify(
            {
                "enabled": bool(AI_ASSISTANT_ENABLED),
                "has_api_key": bool(AI_ASSISTANT_API_KEY),
                "model": str(AI_ASSISTANT_MODEL or ""),
            }
        )

    @app.route("/api/ai/chat", methods=["POST"])
    @login_required
    def ai_assistant_chat():
        """已登录用户的 AI 对话：先走 RAG 检索 → 再调硅基流动 LLM → 提取电影链接。"""
        user_id = session["user_id"]
        payload = request.get_json(silent=True) or {}
        text = (payload.get("text") or "").strip()
        history = payload.get("history") or []
        if not text:
            return jsonify({"error": "请输入消息", "error_category": "bad_request"}), 400

        # 1) RAG 检索：内部 DB + 可选联网搜索
        try:
            rag = run_full_rag_pipeline(text, history=history, user_id=user_id)
        except Exception as e:
            rag = None
            print(f"[AI] RAG 检索异常: {type(e).__name__}: {e}")

        # 2) 没配 API Key：直接返回「RAG 搜索结果 + 未配置提示」的降级纯文本
        if not (AI_ASSISTANT_ENABLED and AI_ASSISTANT_API_KEY):
            reply_lines = []
            reply_lines.append(
                "⚠️ AI 助手未配置 API Key，当前只能为你展示系统内部查询结果。\n"
                "请在 backend/secrets.local 中配置：\n"
                "  AI_ASSISTANT_API_KEY=你的硅基流动API Key\n"
                "免费注册获取：https://cloud.siliconflow.cn/"
            )
            if rag and rag.context_text:
                reply_lines.append("")
                reply_lines.append("📚 系统内部检索到的参考信息：")
                reply_lines.append(rag.context_text[:1200])
            linked_entities = _collect_linked_entities_from_rag(rag)
            return jsonify(
                {
                    "reply": "\n".join(reply_lines).strip(),
                    "linked_entities": linked_entities,
                    "error_category": "backend_503",
                    "error_hint": "未配置 API Key，已自动降级为内部 RAG 展示。",
                }
            )

        # 3) 组装消息 → 调用硅基流动 OpenAI 兼容接口
        trimmed_history = (
            list(history[-AI_ASSISTANT_MAX_HISTORY:]) if isinstance(history, list) else []
        )
        system_content = (
            "你是电影推荐系统的AI助手「小影」，擅长中文回答电影相关问题。\n"
            "回答要求：\n"
            "1) 引用电影名称时必须用中文书名号包裹，例如《流浪地球》。\n"
            "2) 推荐电影时，每部电影给出简短理由（一句话内），按推荐度从高到低排序。\n"
            "3) 如果参考资料不足以回答，坦诚说明并给出可尝试的查询建议，不要编造虚假评分或剧情。\n"
        )
        if rag and rag.context_text:
            system_content += "\n【系统内部参考资料（优先引用，未给出的信息请明确说「未检索到」）】\n" + rag.context_text
        messages = [{"role": "system", "content": system_content}]
        for m in trimmed_history:
            role = m.get("role") if isinstance(m, dict) else None
            content = m.get("content") if isinstance(m, dict) else None
            if role in ("user", "assistant") and isinstance(content, str):
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": text})

        body = {
            "model": AI_ASSISTANT_MODEL,
            "messages": messages,
            "stream": False,
            "temperature": 0.3,
            "max_tokens": 1500,
        }
        url = AI_ASSISTANT_BASE_URL.rstrip("/") + "/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AI_ASSISTANT_API_KEY}",
        }
        from services.http_helper import http_json_request

        data, err_info = http_json_request(
            url,
            method="POST",
            body=body,
            headers=headers,
            timeout=AI_ASSISTANT_TIMEOUT,
            logger_tag="AI_SiliconFlow",
        )

        # 4) 调上游失败：RAG 降级 + 带 category/hint 的错误提示
        if err_info or not data:
            category = _classify_ai_error(err_info, data)
            hint = _ai_error_hint(category)
            reply_lines = []
            if rag and rag.context_text:
                reply_lines.append("📚 系统内部检索到的参考资料（上游AI服务暂时不可用，以下内容仅供参考）：")
                reply_lines.append(rag.context_text[:1000])
                reply_lines.append("")
            reply_lines.append("⚠️ 上游AI服务调用失败，请稍后再试。")
            resp_data = {
                "reply": "\n".join(reply_lines).strip() or "⚠️ 无法连接到AI服务，请检查网络或稍后再试。",
                "linked_entities": _collect_linked_entities_from_rag(rag),
                "error_category": category,
                "error_hint": hint,
            }
            debug_extras = _build_ai_debug_extras(err_info)
            if debug_extras:
                resp_data["error_debug_suggestions"] = debug_extras
            if err_info and isinstance(err_info, dict):
                raw = err_info.get("message") or err_info.get("error")
                if raw and isinstance(raw, str) and len(raw) <= 200:
                    resp_data["error"] = raw
            return jsonify(resp_data), 502 if category in ("upstream_5xx", "backend_502", "backend_504") else 500

        # 5) 解析 LLM 回复：优先取 choices[0].message.content
        reply_text = ""
        try:
            reply_text = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
        except Exception:
            reply_text = ""
        if not reply_text:
            reply_text = "（AI返回了空回复，请换一种问法重试。）"

        # 6) 提取书名号包裹的电影名 → 走内部搜索构造 linked_entities
        linked_entities = _extract_movie_linked_entities_from_reply(
            reply_text, fallback_rag=rag
        )

        resp_data = {
            "reply": reply_text,
            "linked_entities": linked_entities,
        }
        if rag:
            resp_data["_debug_rag"] = {
                "intent": rag.intent,
                "sources_used": rag.sources_used,
            }
        return jsonify(resp_data)

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_frontend(path: str):
        """打包后的前端由 Flask 统一提供，用户只需访问一个地址。"""
        if FRONTEND_DIST.exists():
            target = FRONTEND_DIST / path
            if path and target.is_file():
                return send_from_directory(FRONTEND_DIST, path)
            return send_from_directory(FRONTEND_DIST, "index.html")
        return jsonify(
            {
                "message": "前端尚未打包，请在 frontend 目录执行 npm run build，或使用 npm run dev 开发模式",
                "dev_frontend": "http://127.0.0.1:5173",
                "health": "/api/health",
            }
        )

    return app


app = create_app()

if __name__ == "__main__":
    import threading

    def _background_seed() -> None:
        with app.app_context():
            try:
                count = seed_crawled_ratings()
                history_lines = export_spark_history_ratings_file()
                print(f"ratings seed ready: {count}, history export: {history_lines} lines")
            except Exception as exc:
                print(f"ratings seed skipped: {exc}")

    # 关闭 debug 热重载，避免 Windows 下 watchdog 卡死导致 5000 端口无响应
    threading.Thread(target=_background_seed, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
