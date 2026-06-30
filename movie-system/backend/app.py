"""
FYWZ 电影推荐系统 - Flask 后端主应用

【系统架构】
┌─────────────────────────────────────────────────────────────┐
│                        Flask 应用                           │
├─────────────────────────────────────────────────────────────┤
│                    API 路由层（app.py）                     │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌──────────────┐ ┌─────────────────────┐  │
│  │ 用户认证服务 │ │ 电影数据服务 │ │   数据分析服务       │  │
│  │ (models.py) │ │(movie_service│ │(analytics_service.py│  │
│  │             │ │    .py)      │ │                     │  │
│  └──────┬──────┘ └───────┬──────┘ └──────────┬──────────┘  │
│         │                │                   │              │
│  ┌──────▼──────┐ ┌───────▼──────┐ ┌──────────▼──────────┐  │
│  │   SQLite    │ │    MySQL     │ │    MySQL movies     │  │
│  │ (users等)   │ │(movies表)    │ │    表统计查询        │  │
│  └─────────────┘ └──────────────┘ └─────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                推荐系统服务层                          │  │
│  │  recommend_service.py / recommendation_service.py    │  │
│  │  NMF-ALS协同过滤 + TF-IDF内容推荐 + GraphX社交关系   │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘

【API 路由分类】
  ┌──────────────────────────────────────────────────────┐
  │ 认证模块 (/api/auth)                                  │
  │   POST /register  - 用户注册                          │
  │   POST /login     - 用户登录                          │
  │   POST /logout    - 用户退出                          │
  │   GET  /me        - 获取当前用户                      │
  ├──────────────────────────────────────────────────────┤
  │ 电影模块 (/api/movies)                                │
  │   GET  /movies          - 电影列表（分页/筛选/排序）  │
  │   GET  /movies/home     - 首页电影区块                │
  │   GET  /movies/filters  - 筛选选项                    │
  │   GET  /movies/search   - 搜索建议                    │
  │   GET  /movies/:id      - 电影详情                    │
  │   GET  /movies/:id/similar - 相似电影                │
  │   GET  /movies/:id/trailer - 预告片                  │
  │   GET  /movies/:id/play    - 播放地址                │
  ├──────────────────────────────────────────────────────┤
  │ 视频流模块 (/api/videos, /api/trailers, /api/posters) │
  │   GET  /videos/:id      - 正片视频流                 │
  │   GET  /trailers/:id    - 预告片流                   │
  │   GET  /trailers/local-ids - 本地预告片ID列表        │
  │   GET  /posters/:id     - 海报图片                   │
  ├──────────────────────────────────────────────────────┤
  │ 用户互动模块 (/api/ratings, /api/favorites, /api/comments)│
  │   POST/DELETE /ratings  - 评分（需登录）             │
  │   GET/POST/DELETE /favorites - 收藏（需登录）        │
  │   GET/POST/DELETE /watchlist - 待看片单（需登录）    │
  │   GET/POST/DELETE /lists     - 用户片单（需登录）    │
  │   GET /movies/:id/comments   - 评论列表              │
  │   POST/DELETE /comments      - 评论（需登录）        │
  │   GET  /user/ratings         - 我的评分（需登录）    │
  ├──────────────────────────────────────────────────────┤
  │ 数据分析模块 (/api/analytics)                         │
  │   GET /overview       - 概览统计                     │
  │   GET /filter-options - 筛选选项                     │
  │   GET /genres         - 类型分布                     │
  │   GET /years          - 年份分布                     │
  │   GET /countries      - 国家分布                     │
  │   GET /ratings        - 评分分布                     │
  │   GET /rating-leaderboard - 评分排行榜              │
  │   GET /actors         - 演员分布                     │
  │   GET /directors      - 导演分布                     │
  │   GET /languages      - 语言分布                     │
  │   GET /duration       - 片长分布                     │
  │   GET /reviews        - 影评数分布                   │
  │   GET /awards         - 获奖分布                     │
  │   GET /monthly        - 月度上映分布                 │
  │   GET /country-genre  - 国家-类型关联               │
  │   GET /rating-duration - 评分-时长关联              │
  │   GET /wordcloud      - 词云数据                     │
  │   GET /top            - 高分电影                    │
  │   GET /featured       - 精选电影                    │
  │   GET /movies         - 电影列表（分析用）           │
  │   GET /sources        - 数据源分布                   │
  ├──────────────────────────────────────────────────────┤
  │ 推荐系统模块 (/api/recommend)                         │
  │   GET  /personal      - 个性化推荐（需登录）         │
  │   POST /refresh       - 刷新推荐（触发Spark）        │
  │   GET  /similar/:id   - 相似电影推荐                │
  │   GET  /guest         - 游客推荐（冷启动）           │
  ├──────────────────────────────────────────────────────┤
  │ Spark 模块 (/api/spark)                               │
  │   POST /load-results  - 导入Spark推荐结果            │
  │   POST /export-ratings - 导出评分数据用于Spark       │
  └──────────────────────────────────────────────────────┘

【关键设计】
  1. 双数据库架构：用户数据在 SQLite（SQLAlchemy ORM），电影数据在 MySQL（PyMySQL）
  2. 登录认证：使用 Flask Session（服务端会话存储）
  3. 装饰器 @login_required：保护需要登录的接口
  4. 前端静态文件：打包后的 Vue 前端由 Flask 统一提供
"""

from functools import wraps

from flask import Flask, jsonify, request, send_file, send_from_directory, session
from flask_cors import CORS

from config import DEFAULT_PAGE_SIZE, FRONTEND_DIST, MAX_PAGE_SIZE
from models import Favorite, MovieComment, PlaybackCache, User, UserListItem, UserRating, Watchlist, db
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
    get_similar_movies,
    list_movies,
    parse_crawled_reviews,
    poster_color,
    resolve_poster_file,
    search_suggest,
)
from services.recommendation_service import (
    get_cold_start_movies,
    get_content_similar_movies,
    hybrid_recommendations,
    import_spark_results,
    refresh_spark_recommendations,
)
from services.spark_vm_client import SparkVMError
from services.recommend_service import seed_crawled_ratings
from services.trailer_service import _trailer_memory_cache, get_local_trailer_path, list_local_trailer_ids, resolve_trailer
from services.video_service import (
    get_local_video_path,
    pick_remote_url,
    proxy_video_stream,
    resolve_playback,
)


def _migrate_playback_cache() -> None:
    """
    播放缓存表迁移（兼容旧数据）
    
    职责：
      1. 检查 playback_cache 表是否存在
      2. 若不存在 tmdb_id 列则添加
      3. 删除无效的缓存记录（demo/none类型）
    """
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
    """
    创建 Flask 应用实例
    
    初始化流程：
      1. 创建 Flask 应用
      2. 加载配置（config.py）
      3. 配置 CORS（允许前端跨域）
      4. 初始化 SQLAlchemy（SQLite 用户数据库）
      5. 创建数据库表（若不存在）
      6. 执行播放缓存迁移
    """
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
        """
        登录认证装饰器
        
        用法：@login_required 装饰需要登录的视图函数
        检查 session 中是否存在 user_id，不存在则返回 401
        """
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                return jsonify({"error": "请先登录"}), 401
            return view(*args, **kwargs)

        return wrapped

    # ==================== 健康检查 ====================
    @app.route("/api/health")
    def health():
        """健康检查接口 - 返回系统状态和统计数据"""
        stats = overview_stats(User.query.count(), UserRating.query.count())
        return jsonify({"status": "ok", **stats})

    # ==================== 用户认证 ====================
    @app.route("/api/auth/register", methods=["POST"])
    def register():
        """用户注册"""
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
        """用户登录"""
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
        """用户退出登录"""
        session.pop("user_id", None)
        return jsonify({"message": "已退出登录"})

    @app.route("/api/auth/me")
    def me():
        """获取当前登录用户信息"""
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"user": None})
        user = db.session.get(User, user_id)
        return jsonify({"user": user.to_dict() if user else None})

    # ==================== 电影数据 ====================
    @app.route("/api/movies")
    def movies():
        """
        电影列表接口（分页/筛选/排序）
        
        参数：
          page/page_size - 分页
          genre/genres   - 类型筛选
          languages      - 语言筛选
          year/year_from/year_to - 年份筛选
          keyword/q      - 搜索关键词
          sort           - 排序方式（rating_desc/latest等）
          min_rating/max_rating - 评分范围
          min_votes      - 最小评价人数
        """
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
            sort=sort,
        )
        return jsonify(data)

    @app.route("/api/movies/home")
    def home_sections():
        """首页电影区块（热门、新片、精选等）"""
        return jsonify(get_home_sections())

    @app.route("/api/movies/filters")
    def movie_filters():
        """电影筛选选项（类型、语言、年份等）"""
        return jsonify(get_filter_options())

    @app.route("/api/movies/search")
    def movie_search():
        """搜索建议（输入提示）"""
        keyword = request.args.get("q", "")
        return jsonify({"items": search_suggest(keyword)})

    @app.route("/api/movies/<int:movie_id>")
    def movie_detail(movie_id: int):
        """
        电影详情接口
        
        返回：
          电影完整信息 + 用户互动状态（评分、收藏、待看）
          英雄区主题颜色（用于前端展示）
        """
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
        """相似电影列表"""
        return jsonify({"items": get_similar_movies(movie_id)})

    @app.route("/api/movies/<int:movie_id>/trailer")
    def movie_trailer(movie_id: int):
        """预告片解析"""
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
        """播放地址解析"""
        movie = get_movie_by_id(movie_id)
        if not movie:
            return jsonify({"error": "电影不存在"}), 404
        quality = request.args.get("quality", "auto")
        search_archive = request.args.get("search_archive", "1") != "0"
        return jsonify(resolve_playback(movie, quality=quality, search_archive=search_archive))

    # ==================== 视频流 ====================
    @app.route("/api/videos/<int:movie_id>")
    def stream_video(movie_id: int):
        """正片视频流（本地优先，远程代理兜底）"""
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
        """预告片视频流"""
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
        """本地预告片ID列表"""
        return jsonify({"ids": list_local_trailer_ids()})

    @app.route("/api/posters/<int:movie_id>")
    def poster(movie_id: int):
        """
        海报图片接口
        
        逻辑：
          1. 优先返回本地海报文件
          2. 无本地文件则生成 SVG 占位图（渐变背景+电影名）
        """
        movie = get_movie_by_id(movie_id)
        title = movie["title"] if movie else str(movie_id)
        cover = movie.get("cover_path") if movie else None
        file_path = resolve_poster_file(movie_id, cover)
        if file_path:
            return send_file(file_path)
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

    # ==================== 用户评分 ====================
    @app.route("/api/ratings", methods=["POST", "DELETE"])
    @login_required
    def rate_movie():
        """
        用户评分接口（需登录）
        
        POST  - 新增/更新评分（score: 0.5-10）
        DELETE - 删除评分（?movie_id=xxx）
        """
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

    # ==================== 收藏夹 ====================
    @app.route("/api/favorites", methods=["GET", "POST", "DELETE"])
    @login_required
    def favorites():
        """收藏夹接口（需登录）"""
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

    # ==================== 待看片单 ====================
    @app.route("/api/watchlist", methods=["GET", "POST", "DELETE"])
    @login_required
    def watchlist():
        """待看片单接口（需登录）"""
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

    # ==================== 用户片单 ====================
    @app.route("/api/lists", methods=["GET", "POST", "DELETE"])
    @login_required
    def user_lists():
        """用户片单接口（需登录）"""
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

    # ==================== 评论 ====================
    @app.route("/api/movies/<int:movie_id>/comments", methods=["GET"])
    def movie_comments(movie_id: int):
        """电影评论列表（公开）"""
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
        """评论接口（需登录）"""
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

    # ==================== 我的评分 ====================
    @app.route("/api/user/ratings")
    @login_required
    def my_ratings():
        """我的评分列表（需登录）"""
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

    # ==================== 数据分析辅助 ====================
    def analytics_filters():
        """提取数据分析接口的通用筛选参数"""
        return {
            "genre": request.args.get("genre"),
            "year": request.args.get("year"),
            "country": request.args.get("country"),
        }

    # ==================== 数据分析接口 ====================
    @app.route("/api/analytics/filter-options")
    def analytics_filter_options_route():
        """数据分析筛选选项"""
        genre_limit = min(int(request.args.get("genre_limit", 25)), 50)
        country_limit = min(int(request.args.get("country_limit", 20)), 30)
        year_from = int(request.args.get("year_from", 2010))
        return jsonify(analytics_filter_options(genre_limit, country_limit, year_from))

    @app.route("/api/analytics/overview")
    def analytics_overview():
        """概览统计"""
        return jsonify(
            overview_stats(
                **analytics_filters(),
                user_count=User.query.count(),
                rating_count=UserRating.query.count(),
            )
        )

    @app.route("/api/analytics/genres")
    def analytics_genres():
        """类型分布"""
        limit = min(int(request.args.get("limit", 15)), 50)
        return jsonify(genre_distribution(limit=limit, **analytics_filters()))

    @app.route("/api/analytics/years")
    def analytics_years():
        """年份分布"""
        return jsonify(year_distribution(**analytics_filters()))

    @app.route("/api/analytics/countries")
    def analytics_countries():
        """国家分布"""
        limit = min(int(request.args.get("limit", 12)), 50)
        return jsonify(country_distribution(limit=limit, **analytics_filters()))

    @app.route("/api/analytics/ratings")
    def analytics_ratings():
        """评分区间分布"""
        return jsonify(rating_distribution(**analytics_filters()))

    @app.route("/api/analytics/rating-leaderboard")
    def analytics_rating_leaderboard():
        """评分排行榜"""
        limit = min(int(request.args.get("limit", 10)), 20)
        return jsonify({"items": rating_leaderboard(limit=limit)})

    @app.route("/api/analytics/actors")
    def analytics_actors():
        """演员分布"""
        limit = min(int(request.args.get("limit", 10)), 50)
        return jsonify(actor_distribution(limit=limit, **analytics_filters()))

    @app.route("/api/analytics/top")
    def analytics_top():
        """高分电影列表"""
        limit = min(int(request.args.get("limit", 12)), 50)
        return jsonify(top_movies(limit=limit, **analytics_filters()))

    @app.route("/api/analytics/featured")
    def analytics_featured():
        """精选电影列表"""
        limit = min(int(request.args.get("limit", 12)), 50)
        return jsonify(featured_movies(limit=limit, **analytics_filters()))

    @app.route("/api/analytics/movies")
    def analytics_movies():
        """电影列表（分析用）"""
        limit = min(int(request.args.get("limit", 500)), 1000)
        return jsonify(get_all_movies(limit=limit, **analytics_filters()))

    @app.route("/api/analytics/languages")
    def analytics_languages():
        """语言分布"""
        limit = min(int(request.args.get("limit", 10)), 50)
        return jsonify(language_distribution(limit=limit, **analytics_filters()))

    @app.route("/api/analytics/duration")
    def analytics_duration():
        """片长分布"""
        return jsonify(duration_distribution(**analytics_filters()))

    @app.route("/api/analytics/directors")
    def analytics_directors():
        """导演分布"""
        limit = min(int(request.args.get("limit", 10)), 50)
        return jsonify(director_distribution(limit=limit, **analytics_filters()))

    @app.route("/api/analytics/reviews")
    def analytics_reviews():
        """影评数分布"""
        return jsonify(review_count_distribution(**analytics_filters()))

    @app.route("/api/analytics/country-genre")
    def analytics_country_genre():
        """国家-类型关联"""
        limit = min(int(request.args.get("limit", 8)), 50)
        return jsonify(country_genre_correlation(limit=limit, **analytics_filters()))

    @app.route("/api/analytics/rating-duration")
    def analytics_rating_duration():
        """评分-时长关联"""
        return jsonify(rating_duration_correlation(**analytics_filters()))

    @app.route("/api/analytics/awards")
    def analytics_awards():
        """获奖分布"""
        limit = min(int(request.args.get("limit", 10)), 50)
        return jsonify(award_distribution(limit=limit, **analytics_filters()))

    @app.route("/api/analytics/monthly")
    def analytics_monthly():
        """月度上映分布"""
        return jsonify(monthly_release_distribution(**analytics_filters()))

    @app.route("/api/analytics/wordcloud")
    def analytics_wordcloud():
        """词云数据"""
        limit = min(int(request.args.get("limit", 60)), 120)
        return jsonify(wordcloud_data(limit=limit, **analytics_filters()))

    @app.route("/api/analytics/sources")
    def analytics_sources():
        """数据源分布"""
        return jsonify({"items": source_distribution()})

    # ==================== 推荐系统接口 ====================
    @app.route("/api/recommend/personal")
    @login_required
    def personal_recommend():
        """个性化推荐（需登录，至少3条评分）"""
        user_id = session["user_id"]
        return jsonify(hybrid_recommendations(user_id))

    @app.route("/api/recommend/refresh", methods=["POST"])
    @login_required
    def refresh_recommend():
        """刷新推荐（触发Spark离线计算）"""
        user_id = session["user_id"]
        try:
            return jsonify(refresh_spark_recommendations(user_id))
        except SparkVMError as exc:
            return jsonify({"error": str(exc)}), 503

    @app.route("/api/recommend/similar/<int:movie_id>")
    def graph_similar(movie_id: int):
        """基于内容的相似电影推荐"""
        return jsonify(
            {
                "items": get_content_similar_movies(movie_id),
                "algorithm": "content_tfidf",
            }
        )

    @app.route("/api/recommend/guest")
    def guest_recommend():
        """游客推荐（冷启动，返回热门电影）"""
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

    # ==================== Spark 管理接口 ====================
    @app.route("/api/spark/load-results", methods=["POST"])
    @login_required
    def load_spark_results():
        """导入Spark离线推荐结果"""
        counts = import_spark_results()
        if not counts:
            return jsonify({"error": "未找到 Spark 输出文件，请先在 Ubuntu 运行 spark/run_spark_jobs.sh"}), 404
        total = sum(counts.values())
        return jsonify({"message": "Spark 推荐结果已导入", "count": total, "details": counts})

    @app.route("/api/spark/export-ratings", methods=["POST"])
    @login_required
    def export_ratings_api():
        """导出评分数据用于Spark计算"""
        import sys
        from pathlib import Path

        scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
        sys.path.insert(0, str(scripts_dir))
        from export_spark_ratings import export_ratings

        count = export_ratings()
        return jsonify({"message": "评分数据已导出", "count": count})

    # ==================== 数据预览 ====================
    @app.route("/api/admin/data-preview")
    def data_preview():
        """数据预览（管理用）"""
        sample = list_movies(page=1, page_size=5, sort="latest")
        from models import CrawledRating
        return jsonify(
            {
                "mysql_table": "movies",
                "total_movies": sample["total"],
                "sample_movies": sample["items"],
                "crawled_ratings_count": CrawledRating.query.count(),
                "data_sources": ["豆瓣", "TMDb"],
                "pipeline": ["数据采集", "清洗预处理", "入库", "评分提取", "推荐计算"],
            }
        )

    # ==================== 前端静态文件服务 ====================
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_frontend(path: str):
        """
        前端静态文件服务
        
        逻辑：
          1. 检查前端打包目录是否存在
          2. 若请求具体文件，返回对应文件
          3. 否则返回 index.html（SPA路由）
          4. 未打包时返回提示信息
        """
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
        """后台线程：初始化爬虫评分数据"""
        with app.app_context():
            try:
                count = seed_crawled_ratings()
                print(f"ratings seed ready: {count}")
            except Exception as exc:
                print(f"ratings seed skipped: {exc}")

    # 关闭 debug 热重载，避免 Windows 下 watchdog 卡死导致 5000 端口无响应
    threading.Thread(target=_background_seed, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)