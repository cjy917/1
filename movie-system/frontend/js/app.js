const API = "";
const state = {
  user: null,
  page: 1,
  pages: 1,
  currentMovieId: null,
  authMode: "login",
};

const pages = ["home", "movies", "search", "analytics", "recommend", "detail"];

function $(id) {
  return document.getElementById(id);
}

function showToast(message) {
  const toast = $("toast");
  toast.textContent = message;
  toast.classList.remove("hidden");
  setTimeout(() => toast.classList.add("hidden"), 2600);
}

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "请求失败");
  return data;
}

const PLACEHOLDER_POSTER = "/assets/no-poster.svg";

function renderMovieCard(movie) {
  const posterUrl = movie.poster_url || `/api/posters/${movie.movie_id}`;
  const poster = `<img src="${posterUrl}" alt="${movie.title}" loading="lazy" decoding="async" onerror="this.onerror=null;this.src='${PLACEHOLDER_POSTER}'">`;
  const algoBadge = movie.algorithm
    ? `<span class="badge" style="font-size:10px;margin-top:4px;display:inline-block;">${formatAlgorithm(movie.algorithm)}</span>`
    : "";
  return `
    <article class="movie-card" onclick="openMovie('${movie.movie_id}')">
      ${poster}
      <div class="info">
        <h3>${movie.title}</h3>
        <span class="badge">${movie.rating || movie.score || "-"} 分</span>
        ${algoBadge}
        <div style="margin-top:8px;color:var(--muted);font-size:12px;">${movie.genres || ""}</div>
      </div>
    </article>`;
}

const ALGO_LABELS = {
  als: "ALS协同过滤",
  graphx: "GraphX图协同",
  content: "TF-IDF内容",
  cold_start: "冷启动热门",
  "als+content": "混合推荐",
  "als+graphx": "混合推荐",
  "als+graphx+content": "混合推荐",
};

function formatAlgorithm(algo) {
  if (ALGO_LABELS[algo]) return ALGO_LABELS[algo];
  if (algo.includes("+")) return "混合推荐";
  return algo;
}

function formatRecStrategy(data) {
  const map = {
    hybrid: "Spark 四层混合推荐 (ALS 0.7 + GraphX 0.2 + Content 0.1)",
    cold_start_partial: "冷启动模式 (GraphX + 内容相似)",
    cold_start: "冷启动热门推荐 (评分≥8, 人数≥500)",
    imported: "Spark 离线推荐结果",
  };
  if (data.source === "spark" && data.strategy === "hybrid") return map.hybrid;
  if (data.strategy && map[data.strategy]) return map[data.strategy];
  if (data.source === "spark") return "Spark 个性化推荐";
  return "热门推荐（请运行 Spark 任务）";
}

function showPage(name) {
  pages.forEach((page) => {
    const el = $(`page-${page}`);
    if (el) el.classList.toggle("hidden", page !== name);
  });
  if (name === "analytics") loadAnalytics();
  if (name === "movies") loadMovies();
  if (name === "recommend") loadRecommendations();
  if (name === "home") loadHome();
}

async function refreshUser() {
  const data = await api("/api/auth/me");
  state.user = data.user;
  $("user-label").textContent = state.user ? `欢迎，${state.user.username}` : "未登录";
  $("login-btn").classList.toggle("hidden", !!state.user);
  $("logout-btn").classList.toggle("hidden", !state.user);
}

async function loadHome() {
  const overview = await api("/api/analytics/overview");
  $("stat-movies").textContent = overview.total_movies;
  $("stat-rating").textContent = overview.avg_rating;
  $("stat-reviews").textContent = overview.movies_with_crawled_reviews;
  $("stat-user-ratings").textContent = overview.total_ratings;

  const top = await api("/api/analytics/top");
  $("home-hot-list").innerHTML = top.slice(0, 8).map((item) =>
    renderMovieCard({ movie_id: item.movie_id, title: item.title, rating: item.rating, genres: item.genres, poster_url: `/api/posters/${item.movie_id}` })
  ).join("");

  if (state.user) {
    const rec = await api("/api/recommendations");
    $("rec-source").textContent = formatRecStrategy(rec);
    $("home-rec-list").innerHTML = rec.items.length
      ? rec.items.map((item) => renderMovieCard(item)).join("")
      : `<div class="empty">暂无推荐，请先对电影评分并运行 Spark 推荐任务</div>`;
  } else {
    $("home-rec-list").innerHTML = `<div class="empty">登录后可查看个性化推荐</div>`;
  }
}

async function loadMovies() {
  const genre = $("filter-genre").value.trim();
  const year = $("filter-year").value.trim();
  const sort = $("sort-by").value;
  const params = new URLSearchParams({ page: state.page, page_size: 20, sort });
  if (genre) params.set("genre", genre);
  if (year) params.set("year", year);
  const data = await api(`/api/movies?${params}`);
  state.pages = data.pages || 1;
  $("page-info").textContent = `第 ${data.page} / ${data.pages || 1} 页，共 ${data.total} 部`;
  $("movie-list").innerHTML = data.items.map(renderMovieCard).join("") || `<div class="empty">暂无电影</div>`;
}

async function loadFilters() {
  const data = await api("/api/filters");
  $("genre-list").innerHTML = data.genres.map((g) => `<option value="${g}">`).join("");
}

async function searchMovies() {
  const q = $("search-input").value.trim();
  if (!q) return showToast("请输入搜索关键词");
  const data = await api(`/api/movies/search?q=${encodeURIComponent(q)}`);
  $("search-results").innerHTML = data.items.map(renderMovieCard).join("") || `<div class="empty">未找到相关电影</div>`;
}

async function openMovie(movieId) {
  state.currentMovieId = movieId;
  location.hash = `#detail/${movieId}`;
}

async function loadPlayback(movieId, movie) {
  const loading = $("player-loading");
  const video = $("html5-player");
  const empty = $("player-empty");
  const sourceLabel = $("player-source");
  const actions = $("play-actions");

  loading.classList.remove("hidden");
  video.classList.add("hidden");
  empty.classList.add("hidden");
  video.removeAttribute("src");
  video.load();

  try {
    const playback = await api(`/api/movies/${movieId}/play`);
    loading.classList.add("hidden");

    if (playback.type === "mp4" && playback.stream_url) {
      video.src = playback.stream_url;
      video.classList.remove("hidden");
      sourceLabel.textContent = playback.source === "local" ? "本地正片" : "在线正片";
      actions.innerHTML = `
        <button class="btn btn-primary" onclick="document.getElementById('html5-player').play()">立即播放</button>
        <button class="btn" onclick="document.getElementById('html5-player').requestFullscreen()">全屏</button>
      `;
      return;
    }

    empty.innerHTML = `
      <div>${playback.message || "暂无正片视频"}</div>
      <div style="margin-top:12px;font-size:14px;color:var(--muted);">
        请将 MP4 放到 <code>merged/videos/${movieId}.mp4</code>，或在 CSV 增加「视频地址」列。
      </div>
    `;
    empty.classList.remove("hidden");
    sourceLabel.textContent = "无正片";
    actions.innerHTML = `<button class="btn btn-primary" onclick="loadPlayback('${movieId}', window.__currentMovie)">重新检测</button>`;
  } catch (error) {
    loading.classList.add("hidden");
    empty.textContent = `加载失败：${error.message}`;
    empty.classList.remove("hidden");
  }
}

async function loadDetail(movieId) {
  showPage("detail");
  const movie = await api(`/api/movies/${movieId}`);
  window.__currentMovie = movie;
  $("detail-title").textContent = movie.title;
  $("detail-summary").textContent = movie.summary || "暂无简介";
  $("detail-poster").src = movie.poster_url || `/api/posters/${movieId}`;
  $("detail-poster").onerror = function () {
    this.onerror = null;
    this.src = PLACEHOLDER_POSTER;
  };
  $("crawled-review").textContent = movie.crawled_reviews || "暂无爬虫评论";
  $("translated-review").classList.add("hidden");
  $("translated-review").textContent = "";

  await loadPlayback(movieId, movie);

  $("detail-meta").innerHTML = [
    ["上映年份", movie.release_year],
    ["评分", movie.rating],
    ["类型", movie.genres],
    ["导演", movie.director],
    ["主演", movie.actors],
    ["国家/地区", movie.country],
    ["语言", movie.language],
    ["片长", movie.duration ? `${movie.duration} 分钟` : "-"],
  ].map(([label, value]) => `<div class="meta-item"><label>${label}</label><div>${value || "-"}</div></div>`).join("");

  renderRatingStars(movie.my_rating);
  const reviews = await api(`/api/movies/${movieId}/reviews`);
  $("user-reviews").innerHTML = reviews.items.length
    ? reviews.items.map((r) => `<div class="review-item"><strong>${r.username}</strong><p>${r.content}</p><small>${r.created_at || ""}</small></div>`).join("")
    : `<div class="empty">还没有用户评论</div>`;

  const similar = await api(`/api/recommendations/similar/${movieId}`);
  $("similar-list").innerHTML = similar.items.map(renderMovieCard).join("");
}

function renderRatingStars(myRating) {
  const container = $("rating-stars");
  container.innerHTML = "";
  for (let score = 1; score <= 10; score += 0.5) {
    const btn = document.createElement("button");
    btn.textContent = score;
    if (myRating && Math.abs(myRating - score) < 0.01) btn.classList.add("active");
    btn.onclick = async () => {
      if (!state.user) return showToast("请先登录后评分");
      await api(`/api/movies/${state.currentMovieId}/rate`, {
        method: "POST",
        body: JSON.stringify({ score }),
      });
      showToast("评分成功");
      renderRatingStars(score);
      $("my-rating-text").textContent = `我的评分：${score}`;
    };
    container.appendChild(btn);
  }
  $("my-rating-text").textContent = myRating ? `我的评分：${myRating}` : "点击星星评分（0.5-10）";
}

async function loadRecommendations() {
  if (!state.user) {
    $("recommend-list").innerHTML = `<div class="empty">请先登录查看推荐结果</div>`;
    $("rec-strategy-desc").textContent = "";
    return;
  }
  const data = await api("/api/recommendations");
  $("rec-strategy-desc").textContent = formatRecStrategy(data);
  $("recommend-list").innerHTML = data.items.length
    ? data.items.map((item) => renderMovieCard(item)).join("")
    : `<div class="empty">暂无推荐结果。请运行 Spark 任务后导入，或先给电影评分。</div>`;
}

async function loadAnalytics() {
  const [genres, years, countries, ratings, languages, top] = await Promise.all([
    api("/api/analytics/genres"),
    api("/api/analytics/years"),
    api("/api/analytics/countries"),
    api("/api/analytics/ratings"),
    api("/api/analytics/languages"),
    api("/api/analytics/top"),
  ]);

  renderPie("chart-genres", "电影类型分布", genres);
  renderBar("chart-years", "上映年份分布", years.map((x) => x.year), years.map((x) => x.count));
  renderPie("chart-countries", "国家/地区分布", countries);
  renderBar("chart-ratings", "评分区间分布", ratings.map((x) => x.range), ratings.map((x) => x.count));
  renderPie("chart-languages", "语言分布", languages);
  renderBar("chart-top", "Top10 高分电影", top.map((x) => x.title), top.map((x) => x.rating), true);
}

function renderPie(elementId, title, data) {
  const chart = echarts.init($(elementId));
  chart.setOption({
    backgroundColor: "transparent",
    title: { text: title, textStyle: { color: "#e8edf7" } },
    tooltip: { trigger: "item" },
    series: [{ type: "pie", radius: ["35%", "65%"], data }],
  });
}

function renderBar(elementId, title, labels, values, rotate = false) {
  const chart = echarts.init($(elementId));
  chart.setOption({
    backgroundColor: "transparent",
    title: { text: title, textStyle: { color: "#e8edf7" } },
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: labels, axisLabel: { color: "#9aa7c0", rotate: rotate ? 30 : 0 } },
    yAxis: { type: "value", axisLabel: { color: "#9aa7c0" } },
    series: [{ type: "bar", data: values, itemStyle: { color: "#5b8cff" } }],
  });
}

function openAuth(mode = "login") {
  state.authMode = mode;
  $("auth-title").textContent = mode === "login" ? "用户登录" : "用户注册";
  $("auth-submit").textContent = mode === "login" ? "登录" : "注册";
  $("auth-toggle").textContent = mode === "login" ? "去注册" : "去登录";
  $("auth-email-group").classList.toggle("hidden", mode === "login");
  $("auth-modal").classList.remove("hidden");
}

function closeAuth() {
  $("auth-modal").classList.add("hidden");
}

async function submitAuth() {
  const username = $("auth-username").value.trim();
  const password = $("auth-password").value;
  const email = $("auth-email").value.trim();
  try {
    if (state.authMode === "login") {
      await api("/api/auth/login", { method: "POST", body: JSON.stringify({ username, password }) });
      showToast("登录成功");
    } else {
      await api("/api/auth/register", { method: "POST", body: JSON.stringify({ username, password, email }) });
      showToast("注册成功");
    }
    closeAuth();
    await refreshUser();
    loadHome();
  } catch (error) {
    showToast(error.message);
  }
}

function handleRoute() {
  const hash = location.hash.replace("#", "") || "home";
  if (hash.startsWith("detail/")) {
    const movieId = hash.split("/")[1];
    state.currentMovieId = movieId;
    loadDetail(movieId);
    return;
  }
  showPage(hash);
}

$("login-btn").onclick = () => openAuth("login");
$("logout-btn").onclick = async () => {
  await api("/api/auth/logout", { method: "POST" });
  state.user = null;
  await refreshUser();
  showToast("已退出");
};
$("auth-close").onclick = closeAuth;
$("auth-toggle").onclick = () => openAuth(state.authMode === "login" ? "register" : "login");
$("auth-submit").onclick = submitAuth;
$("apply-filter-btn").onclick = () => { state.page = 1; loadMovies(); };
$("prev-page").onclick = () => { if (state.page > 1) { state.page -= 1; loadMovies(); } };
$("next-page").onclick = () => { if (state.page < state.pages) { state.page += 1; loadMovies(); } };
$("search-btn").onclick = searchMovies;
$("search-input").addEventListener("keydown", (e) => { if (e.key === "Enter") searchMovies(); });
$("translate-review-btn").onclick = async () => {
  const text = $("crawled-review").textContent.trim();
  if (!text || text === "暂无爬虫评论") return showToast("没有可翻译的内容");
  try {
    const data = await api("/api/translate", { method: "POST", body: JSON.stringify({ text }) });
    $("translated-review").textContent = data.translated;
    $("translated-review").classList.remove("hidden");
    showToast("翻译完成");
  } catch (error) {
    showToast(error.message);
  }
};
$("submit-review-btn").onclick = async () => {
  if (!state.user) return showToast("请先登录");
  const content = $("review-input").value.trim();
  if (!content) return showToast("评论不能为空");
  await api(`/api/movies/${state.currentMovieId}/reviews`, { method: "POST", body: JSON.stringify({ content }) });
  $("review-input").value = "";
  showToast("评论成功");
  loadDetail(state.currentMovieId);
};
$("load-spark-rec-btn").onclick = async () => {
  try {
    const data = await api("/api/spark/load-results", { method: "POST", body: "{}" });
    showToast(`${data.message}（${data.count} 条）`);
    loadRecommendations();
  } catch (error) {
    showToast(error.message);
  }
};

window.openMovie = openMovie;
window.addEventListener("hashchange", handleRoute);

(async function init() {
  await refreshUser();
  await loadFilters();
  handleRoute();
})();
