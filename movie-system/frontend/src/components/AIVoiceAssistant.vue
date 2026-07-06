<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { aiAssistantApi } from '../api'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

const STORAGE_KEY = 'fywz_ai_assistant_state_v1'
const HISTORY_KEY = 'fywz_ai_assistant_history_v1'
const POSITION_KEY = 'fywz_ai_assistant_position_v1'

const SNAP_DISTANCE = 30
const DRAG_THRESHOLD = 3
const _TITLE_NORM_REGEX = /[0-9０-９①②③④⑤⑥⑦⑧⑨⑩ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ·・\-_/\\:：;；,，.。!！?？\s'\""''`~!@#$%^&*()（）【】\[\]{}<>《》]/g
const _BOOK_TITLE_REGEX = /《([^》]{1,50})》/g
const _normalizeTitle = s => String(s || '').replace(_TITLE_NORM_REGEX, '').toLowerCase()

const savedState = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null')
const savedHistory = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]')
const savedPosition = JSON.parse(localStorage.getItem(POSITION_KEY) || 'null')

const visible = ref(savedState?.visible ?? true)
const minimized = ref(savedState?.minimized ?? true)
const messages = ref(savedHistory.length ? savedHistory : [])
const inputText = ref('')
const isLoading = ref(false)
const isRecording = ref(false)
const isSpeaking = ref(false)
const config = ref({ enabled: true, has_api_key: false, model: '' })
const configError = ref('')
const chatContainer = ref(null)
const inputRef = ref(null)
const userLoaded = ref(false)
const panelRef = ref(null)
const headerRef = ref(null)

const isDragging = ref(false)
const panelPosition = reactive({
  right: savedPosition?.right ?? null,
  bottom: savedPosition?.bottom ?? null,
  left: savedPosition?.left ?? null,
  top: savedPosition?.top ?? null,
})

let _dragState = null
function _createDragState(e) {
  const rect = panelRef.value.getBoundingClientRect()
  const viewportW = window.innerWidth
  const viewportH = window.innerHeight
  return {
    pointerId: e.pointerId,
    startPointerX: e.clientX,
    startPointerY: e.clientY,
    startLeft: rect.left,
    startTop: rect.top,
    panelW: rect.width,
    panelH: rect.height,
    viewportW,
    viewportH,
    moved: false,
  }
}

function _clamp(v, min, max) {
  return Math.max(min, Math.min(max, v))
}

function _applySnap(left, top, panelW, panelH, viewportW, viewportH) {
  let snappedLeft = left
  let snappedTop = top
  if (left <= SNAP_DISTANCE) snappedLeft = 0
  else if (left + panelW >= viewportW - SNAP_DISTANCE) snappedLeft = viewportW - panelW
  if (top <= SNAP_DISTANCE) snappedTop = 0
  else if (top + panelH >= viewportH - SNAP_DISTANCE) snappedTop = viewportH - panelH
  return { left: snappedLeft, top: snappedTop }
}

function _persistPosition(left, top, panelW, panelH, viewportW, viewportH) {
  const useRight = left > viewportW / 2
  const useBottom = top > viewportH / 2
  const pos = {
    left: useRight ? null : left,
    top: useBottom ? null : top,
    right: useRight ? viewportW - (left + panelW) : null,
    bottom: useBottom ? viewportH - (top + panelH) : null,
  }
  panelPosition.left = pos.left
  panelPosition.top = pos.top
  panelPosition.right = pos.right
  panelPosition.bottom = pos.bottom
  try {
    localStorage.setItem(POSITION_KEY, JSON.stringify(pos))
  } catch (_) {}
}

function onHeaderPointerDown(e) {
  if (e.button !== undefined && e.button !== 0) return
  if (minimized.value) return
  const target = e.target
  if (target.closest('.header-actions')) return
  if (target.closest('.header-left')) {
    const actions = target.closest('.header-left')
    if (actions && (target.tagName === 'BUTTON' || target.closest('button'))) return
  }
  e.preventDefault()
  _dragState = _createDragState(e)
  isDragging.value = true
  try {
    headerRef.value.setPointerCapture(_dragState.pointerId)
  } catch (_) {}
  window.addEventListener('pointermove', onWindowPointerMove, true)
  window.addEventListener('pointerup', onWindowPointerUp, true)
  window.addEventListener('pointercancel', onWindowPointerUp, true)
}

function onWindowPointerMove(e) {
  if (!_dragState) return
  const s = _dragState
  const dx = e.clientX - s.startPointerX
  const dy = e.clientY - s.startPointerY
  if (!s.moved && (Math.abs(dx) > DRAG_THRESHOLD || Math.abs(dy) > DRAG_THRESHOLD)) {
    s.moved = true
  }
  const viewportW = window.innerWidth
  const viewportH = window.innerHeight
  let nextLeft = s.startLeft + dx
  let nextTop = s.startTop + dy
  nextLeft = _clamp(nextLeft, 0, viewportW - s.panelW)
  nextTop = _clamp(nextTop, 0, viewportH - s.panelH)
  if (!s.moved) return
  panelPosition.left = nextLeft
  panelPosition.top = nextTop
  panelPosition.right = null
  panelPosition.bottom = null
}

function onWindowPointerUp() {
  window.removeEventListener('pointermove', onWindowPointerMove, true)
  window.removeEventListener('pointerup', onWindowPointerUp, true)
  window.removeEventListener('pointercancel', onWindowPointerUp, true)
  if (!_dragState) return
  const s = _dragState
  try {
    if (headerRef.value) headerRef.value.releasePointerCapture(s.pointerId)
  } catch (_) {}
  if (s.moved) {
    const viewportW = window.innerWidth
    const viewportH = window.innerHeight
    const rect = panelRef.value.getBoundingClientRect()
    const snapped = _applySnap(rect.left, rect.top, s.panelW, s.panelH, viewportW, viewportH)
    panelPosition.left = snapped.left
    panelPosition.top = snapped.top
    panelPosition.right = null
    panelPosition.bottom = null
    nextTick(() => {
      _persistPosition(snapped.left, snapped.top, s.panelW, s.panelH, viewportW, viewportH)
    })
  }
  _dragState = null
  isDragging.value = false
}

const rootStyle = computed(() => {
  const style = {}
  if (panelPosition.left !== null) style.left = `${panelPosition.left}px`
  else if (panelPosition.right !== null) style.right = `${panelPosition.right}px`
  else style.right = '24px'
  if (panelPosition.top !== null) style.top = `${panelPosition.top}px`
  else if (panelPosition.bottom !== null) style.bottom = `${panelPosition.bottom}px`
  else style.bottom = '24px'
  style.zIndex = 9999
  return style
})

function onHeaderLeftClick() {
  if (_dragState && _dragState.moved) return
  minimized.value = !minimized.value
}

// ── F4 修复：连点请求竞态拦截。每次sendMessage递增。只有reqId等于 _lastIssuedReqId 的回调才允许push消息到messages
let _nextRequestSeq = 0
const _lastIssuedReqId = ref(0)

let recognition = null
let synth = null

const isLoggedIn = computed(() => userStore.isLoggedIn)

function _cleanupVoiceIO() {
  stopSpeaking()
  if (recognition && isRecording.value) recognition.stop()
}

function goLogin() {
  _cleanupVoiceIO()
  router.push({ name: 'login' })
}

function goRegister() {
  _cleanupVoiceIO()
  router.push({ name: 'register' })
}

function persistState() {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({ visible: visible.value, minimized: minimized.value })
  )
}

function persistHistory() {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(messages.value.slice(-50)))
}

watch([visible, minimized], persistState)
watch(messages, persistHistory, { deep: true })

watch(isLoggedIn, (logged) => {
  if (logged && userLoaded.value) {
    loadConfig().catch(() => {})
    if (messages.value.length === 0) {
      messages.value.push({
        role: 'assistant',
        content: '你好！我是你的AI智能语音助手「小影」🎬。我可以帮你推荐电影、查询电影信息、解答数据分析问题。\n\n💡 小提示：点击🎤可以语音输入，点击🔊可以朗读回答。',
        time: Date.now(),
        isWelcome: true,
      })
    }
  }
})

function scrollToBottom() {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

async function loadConfig() {
  if (!isLoggedIn.value) return
  try {
    const { data } = await aiAssistantApi.config()
    config.value = data
  } catch (e) {
    console.warn('AI assistant config load failed:', e)
  }
}

function initSpeechRecognition() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!SR) return null
  const rec = new SR()
  rec.lang = 'zh-CN'
  rec.continuous = false
  rec.interimResults = true
  rec.onstart = () => {
    isRecording.value = true
  }
  rec.onend = () => {
    isRecording.value = false
  }
  rec.onerror = (e) => {
    console.warn('Speech recognition error:', e.error)
    isRecording.value = false
  }
  rec.onresult = (event) => {
    let transcript = ''
    for (let i = event.resultIndex; i < event.results.length; i++) {
      transcript += event.results[i][0].transcript
    }
    inputText.value = transcript
  }
  return rec
}

function initSpeechSynthesis() {
  return window.speechSynthesis || null
}

function toggleRecording() {
  if (!isLoggedIn.value) {
    goLogin()
    return
  }
  if (!recognition) {
    alert('当前浏览器不支持语音识别功能，请使用 Chrome 或 Edge 浏览器，或直接使用文本输入。')
    return
  }
  if (isRecording.value) {
    recognition.stop()
  } else {
    stopSpeaking()
    try {
      recognition.start()
    } catch (e) {
      console.warn('Recognition start error:', e)
    }
  }
}

function speak(text) {
  if (!isLoggedIn.value) return
  if (!synth || !text) return
  stopSpeaking()
  const utter = new SpeechSynthesisUtterance(text)
  utter.lang = 'zh-CN'
  utter.rate = 1.0
  utter.pitch = 1.0
  utter.onstart = () => { isSpeaking.value = true }
  utter.onend = () => { isSpeaking.value = false }
  utter.onerror = () => { isSpeaking.value = false }
  synth.speak(utter)
}

function stopSpeaking() {
  if (synth) {
    synth.cancel()
  }
  isSpeaking.value = false
}

async function sendMessage() {
  if (!isLoggedIn.value) {
    goLogin()
    return
  }
  const text = inputText.value.trim()
  if (!text || isLoading.value) return
  if (!config.value.enabled) {
    configError.value = 'AI助手功能未启用'
    return
  }
  if (!config.value.has_api_key) {
    configError.value =
      'AI助手未配置 API Key。请在 backend/secrets.local 中设置 AI_ASSISTANT_API_KEY=你的硅基流动API Key。注册免费获取：https://cloud.siliconflow.cn/'
    return
  }
  configError.value = ''

  stopSpeaking()
  messages.value.push({ role: 'user', content: text, time: Date.now() })
  inputText.value = ''
  isLoading.value = true
  scrollToBottom()

  // F4 竞态拦截：发请求前先分配唯一递增reqId，并更新"最新已发出请求ID"
  _nextRequestSeq += 1
  const myReqId = _nextRequestSeq
  _lastIssuedReqId.value = myReqId

  const historyForApi = messages.value
    .slice(0, -1)
    .filter((m) => m.role === 'user' || m.role === 'assistant')
    .filter((m) => {
      if (!m || !m.content) return false
      const txt = String(m.content).trim()
      if (m.isWelcome || m.isError) return false
      if (txt.length < 2) return false
      // 排除重复的 UI 提示或误识别的“点击”噪声
      if (/^点击+$/u.test(txt)) return false
      return true
    })
    .map((m) => ({ role: m.role, content: m.content }))

  try {
    const uid = userStore.user?.id ?? null
    const { data } = await aiAssistantApi.chat(text, historyForApi, uid)

    // F4 竞态拦截：只有"我这次请求ID"等于最新发出的ID时才允许写入messages
    //   防止用户先问吴京、后问张艺谋，吴京返回慢把消息插到最新张艺谋回复之后，显示错乱
    if (myReqId !== _lastIssuedReqId.value) {
      console.debug(`[AIVoiceAssistant] 竞态拦截：跳过旧reqId=${myReqId}，最新=${_lastIssuedReqId.value}`)
      isLoading.value = false
      return
    }
    messages.value.push({
      role: 'assistant',
      content: data.reply,
      linked_entities: data.linked_entities || [],
      time: Date.now(),
    })
    scrollToBottom()
    speak(data.reply)
  } catch (e) {
    const status = e?.response?.status
    const respData = e?.response?.data || {}
    const backendCategory = respData.error_category
    const backendHint = respData.error_hint
    const backendDebug = respData.error_debug_suggestions
    const frontendCategory = e.fywzCategory
    const frontendHint = e.fywzHint
    const category = backendCategory || frontendCategory || 'unknown'
    const hint = backendHint || frontendHint || ''

    const lines = []
    const titleMap = {
      timeout: '⏱️ AI服务请求超时',
      dns_failed: '🌐 DNS解析失败',
      proxy_connection_refused: '🔌 代理连接被拒绝',
      network_unreachable: '📡 网络不可达',
      ssl_error: '🔒 SSL证书错误',
      auth_failed: '🔑 API Key无效',
      rate_limited: '🚦 请求频率超限',
      upstream_5xx: '⚠️ 上游AI服务5xx错误',
      backend_504: '⏳ 后端访问AI服务超时（504）',
      upstream_502: '🔌 上游AI服务异常（502）',
      backend_503: '🚫 AI功能未就绪（503）',
      frontend_timeout: '⏳ 前端请求超时（60秒）',
      frontend_network: '🌐 前端无法连接后端',
      auth_401: '🔐 未登录或登录过期',
      not_found: '❓ API路由不存在',
      bad_request: '⚠️ 请求参数错误',
    }
    const title = titleMap[category] || '❌ 请求失败'
    lines.push(title)
    lines.push('')

    const rawErr = respData.error || e?.response?.data?.error || e?.message || '请求失败，请稍后重试。'
    if (rawErr && String(rawErr).length <= 200) {
      lines.push('原始错误：' + rawErr)
      lines.push('')
    }

    if (hint) {
      lines.push('💡 建议：' + hint)
      lines.push('')
    }
    if (backendDebug) {
      lines.push('🔧 快速排查步骤：' + backendDebug)
    }

    const proxiesUsed = respData.proxies_used
    const httpProxySet = respData.http_proxy_configured
    const httpsProxySet = respData.https_proxy_configured
    if (proxiesUsed !== undefined) {
      lines.push('')
      lines.push(
        '代理状态：' +
          (proxiesUsed ? '已走代理' : '直连（未走代理）') +
          `，配置 HTTP_PROXY=${httpProxySet ? '✅' : '❌'} HTTPS_PROXY=${httpsProxySet ? '✅' : '❌'}，` +
          '如不对请修改 backend/secrets.local 中的 HTTP_PROXY/HTTPS_PROXY 后重启 Flask。'
      )
    }

    if (status === 401 || category === 'auth_401') {
      messages.value.push({
        role: 'assistant',
        content: '⚠️ 登录状态已过期，请先登录后再使用AI助手功能。',
        time: Date.now(),
        isError: true,
      })
    } else {
      messages.value.push({
        role: 'assistant',
        content: lines.join('\n').trim(),
        time: Date.now(),
        isError: true,
      })
    }
    scrollToBottom()
  } finally {
    isLoading.value = false
  }
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

function toggleWindow() {
  if (!visible.value) {
    visible.value = true
    minimized.value = false
    nextTick(() => inputRef.value?.focus())
  } else if (minimized.value) {
    minimized.value = false
    nextTick(() => inputRef.value?.focus())
  } else {
    minimized.value = true
    _cleanupVoiceIO()
  }
  scrollToBottom()
}

function closeWindow() {
  visible.value = false
  minimized.value = true
  _cleanupVoiceIO()
}

function openFromClosed() {
  visible.value = true
  minimized.value = false
  nextTick(() => inputRef.value?.focus())
  scrollToBottom()
}

function clearChat() {
  if (!isLoggedIn.value) {
    goLogin()
    return
  }
  if (confirm('确定要清空所有对话记录吗？')) {
    messages.value = []
    stopSpeaking()
  }
}

/**
 * 将AI回答内容按linked_entities拆分为「普通文本片段」和「可点击电影链接片段」
 * 保证顺序与原文本一致，适合v-for渲染。
 * 兼容：旧消息没有linked_entities时整体作为一个文本片段。
 * 优化：
 * 1) 前置entities去重，避免后端返回重复实体时while循环叠加扫同一文本多次
 * 2) 单条消息中同一个电影title出现超2次 → 后续出现的降级为普通text，避免刷屏
 * 3) 完整书名号token长度≠entity长度（例：entity《流浪地球》匹配到content中《流浪地球2战》）：
 *    → 用content中的完整书名号token作为link的显示文本，保证用户看到的"2战"后缀不丢失
 */
function parseLinkedContent(content, linkedEntities) {
  const segments = []
  if (!content) return segments
  const rawEntities = Array.isArray(linkedEntities)
    ? linkedEntities.filter(e => e && e.type === 'movie' && e.text)
    : []
  // ── F2 修复1：entities前置去重（text+movie_id复合键），避免同一实体重复扫全文 ──
  const seenEntKeys = new Set()
  const entities = []
  for (const e of rawEntities) {
    const k = `${e.text}||${e.movie_id ?? ''}||${e.title ?? ''}`
    if (seenEntKeys.has(k)) continue
    seenEntKeys.add(k)
    entities.push(e)
  }
  if (entities.length === 0) {
    segments.push({ kind: 'text', value: content })
    return segments
  }

  const positions = []
  for (const ent of entities) {
    const t = ent.text
    let from = 0
    while (true) {
      const idx = content.indexOf(t, from)
      if (idx === -1) break

      // F3 修复：书名号token对齐增强
      //   - 若entity是《X》包裹，找content中从该位置开始的第一个完整《...》token的范围
      //   - 如果完整token和entity长度不同 → 不丢弃此匹配！
      //       以前是"短吃长则跳过"，现在改成：用完整的content中书名号token范围做position，
      //       显示文本用完整token（保留"2战"后缀），movie_id仍然用entity的。
      if (t.startsWith('《') && t.endsWith('》')) {
        const tokenStart = idx // content[idx] 就是 entity 开头的《
        const closeIdx = content.indexOf('》', tokenStart + 1)
        if (closeIdx !== -1) {
          // 这是content中从当前《到下一个》的完整书名号token
          const tokenLen = closeIdx - tokenStart + 1
          if (tokenLen !== t.length) {
            // 长度不一致 → 以前直接放弃；现在：把完整书名号token当作显示文本的position
            positions.push({
              start: tokenStart,
              end: closeIdx + 1,
              len: tokenLen,
              entity: Object.assign({}, ent, {
                // 覆盖显示text字段为完整书名号token（保证"2战"不丢）
                _display_text: content.slice(tokenStart, closeIdx + 1),
              }),
            })
            from = closeIdx + 1
            continue
          }
        }
      }

      positions.push({ start: idx, end: idx + t.length, len: t.length, entity: ent })
      from = idx + t.length
    }
  }
  if (positions.length === 0) {
    segments.push({ kind: 'text', value: content })
    return segments
  }
  // 先按start升序；若同start则长的优先（长entity覆盖短entity）
  positions.sort((a, b) => a.start - b.start || (b.len - a.len))
  const merged = []
  for (const p of positions) {
    const last = merged[merged.length - 1]
    if (last && p.start < last.end) continue
    merged.push(p)
  }
  let cursor = 0
  // ── F2 修复2：单条消息中同一title出现超2次 → 从第3次开始降级为普通text ──
  const titleOccurCount = new Map()
  const MAX_LINK_PER_TITLE = 2

  for (const pos of merged) {
    if (pos.start > cursor) segments.push({ kind: 'text', value: content.slice(cursor, pos.start) })
    const rawTitle = pos.entity.title || (pos.entity._display_text || pos.entity.text).replace(/^《|》$/g, '')
    const n = (titleOccurCount.get(rawTitle) || 0) + 1
    titleOccurCount.set(rawTitle, n)
    const displayValue = pos.entity._display_text || pos.entity.text
    if (n <= MAX_LINK_PER_TITLE) {
      segments.push({
        kind: 'movie-link',
        value: displayValue,
        movie_id: pos.entity.movie_id || null,
        title: pos.entity.title || rawTitle,
      })
    } else {
      // 第3+次重复出现 → 只渲染为普通文本，不做链接了，避免刷屏
      segments.push({ kind: 'text', value: displayValue })
    }
    cursor = pos.end
  }
  if (cursor < content.length) segments.push({ kind: 'text', value: content.slice(cursor) })
  return segments.length ? segments : [{ kind: 'text', value: content }]
}

/**
 * 前端兜底：title→movie_id 的响应式缓存
 * 如果后端linked_entities未命中（如模型复述时RAG没检索到），前端调用/api/movies/search异步补全
 */
const _movieTitleIdCache = reactive(new Map())
const _movieFetchingSet = reactive(new Set())

async function _ensureMovieIdByTitle(title) {
  if (!title) return null
  const key = String(title).trim()
  if (_movieTitleIdCache.has(key)) return _movieTitleIdCache.get(key) || null
  if (_movieFetchingSet.has(key)) return null
  _movieFetchingSet.add(key)
  try {
    const url = `/api/movies/search?q=${encodeURIComponent(key)}`
    const resp = await fetch(url, { credentials: 'same-origin', headers: { 'Accept': 'application/json' } })
    const json = resp.ok ? await resp.json() : {}
    const items = (json && json.items) ? json.items : []
    let bestExact = null
    let bestNormEq = null
    let bestPrefix = null
    const nKey = _normalizeTitle(key)
    for (const it of items) {
      const h = (it.title || '').trim()
      const rawMid = it.movie_id || it.id
      if (!h || !rawMid) continue
      const midNum = Number(rawMid)
      if (!midNum) continue
      if (h === key) {
        bestExact = midNum
        break
      }
      const nHit = _normalizeTitle(h)
      const lenDiff = Math.abs(h.length - key.length)
      if (!bestNormEq && nKey && nHit && nKey === nHit && nKey.length >= 2 && lenDiff <= 2) {
        bestNormEq = midNum
      }
      if (!bestPrefix && (h.startsWith(key) || key.startsWith(h)) && lenDiff <= 3) {
        bestPrefix = midNum
      }
    }
    const found = bestExact || bestNormEq || bestPrefix
    _movieTitleIdCache.set(key, found || 0)
    const matchTag = bestExact ? 'EXACT' : bestNormEq ? 'NORM-EQ' : bestPrefix ? 'PREFIX' : null
    if (matchTag) {
      console.log(`[AI_LINK_FE] 前端补查《${key}》 -> movie_id=${found} (${matchTag})`)
    } else {
      console.log(`[AI_LINK_FE] 前端补查《${key}》 -> 无匹配`)
    }
    return found
  } catch (e) {
    console.warn(`[AI_LINK_FE] 前端补查异常《${key}》:`, e)
    return null
  } finally {
    _movieFetchingSet.delete(key)
  }
}

/**
 * 供模板使用：返回消息的渲染片段数组，自动触发缺失movie_id的前端异步兜底搜索
 * 只要调用过_ensureMovieIdByTitle并返回后，响应式Map会变化，触发视图重新渲染（把fallback span升级为router-link）
 */
function getRenderSegments(msg) {
  const base = parseLinkedContent(msg.content, msg.linked_entities)
  const allTitlesInText = new Set()
  const content = msg.content || ''
  let m
  while ((m = _BOOK_TITLE_REGEX.exec(content)) !== null) {
    allTitlesInText.add(m[1].trim())
  }
  const hasAnyLink = base.some(s => s.kind === 'movie-link')
  let finalSegs = base
  if (!hasAnyLink && allTitlesInText.size > 0) {
    const fakeEntities = Array.from(allTitlesInText).map(t => ({
      type: 'movie', text: `《${t}》`, title: t, movie_id: _movieTitleIdCache.get(t) || null,
    }))
    finalSegs = parseLinkedContent(content, fakeEntities)
  }
  for (const seg of finalSegs) {
    if (seg.kind !== 'movie-link' || seg.movie_id || !seg.title) continue
    const cached = _movieTitleIdCache.get(seg.title)
    if (cached > 0) {
      seg.movie_id = cached
    } else if (cached !== 0 && !_movieFetchingSet.has(seg.title)) {
      _ensureMovieIdByTitle(seg.title).then(mid => {
        if (mid) seg.movie_id = mid
      })
    }
  }
  return finalSegs
}

onMounted(async () => {
  try {
    await userStore.fetchMe()
  } finally {
    userLoaded.value = true
  }
  if (isLoggedIn.value) {
    await loadConfig()
    recognition = initSpeechRecognition()
    synth = initSpeechSynthesis()
    if (messages.value.length === 0) {
      messages.value.push({
        role: 'assistant',
        content: '你好！我是你的AI智能语音助手「小影」🎬。我可以帮你推荐电影、查询电影信息、解答数据分析问题。\n\n💡 小提示：点击🎤可以语音输入，点击🔊可以朗读回答。',
        time: Date.now(),
        isWelcome: true,
      })
    }
  } else {
    recognition = initSpeechRecognition()
    synth = initSpeechSynthesis()
  }
})

onBeforeUnmount(() => {
  _cleanupVoiceIO()
  window.removeEventListener('pointermove', onWindowPointerMove, true)
  window.removeEventListener('pointerup', onWindowPointerUp, true)
  window.removeEventListener('pointercancel', onWindowPointerUp, true)
  _dragState = null
})
</script>

<template>
  <div class="ai-assistant-root" :style="rootStyle" aria-live="polite">
    <Transition name="fab-pop">
      <button
        v-if="!visible"
        class="fab-btn"
        @click="openFromClosed"
        aria-label="打开AI智能语音小助手"
        title="AI智能语音小助手"
      >
        <span class="fab-icon">🎬</span>
        <span class="fab-label">AI助手</span>
      </button>
    </Transition>

    <Transition name="panel-slide">
      <div ref="panelRef" v-if="visible" class="ai-panel" :class="{ 'is-minimized': minimized, 'is-dragging': isDragging }">
        <div
          ref="headerRef"
          class="panel-header"
          :class="{ 'is-draggable': !minimized }"
          @pointerdown="onHeaderPointerDown"
        >
          <div class="header-left" @click="onHeaderLeftClick" style="cursor:pointer">
            <span class="avatar">🎬</span>
            <div class="titles">
              <div class="title">AI智能语音小助手</div>
              <div class="subtitle">
                <span v-if="config.model" class="model-tag">{{ config.model.split('/').pop() }}</span>
                <span v-if="config.has_api_key" class="status status-ok">● 已连接</span>
                <span v-else class="status status-warn">● 未配置Key</span>
              </div>
            </div>
          </div>
          <div class="header-actions">
            <button v-if="messages.length > 1" class="icon-btn" @click="clearChat" title="清空对话" aria-label="清空对话">
              🗑️
            </button>
            <button class="icon-btn" @click="toggleWindow" :title="minimized ? '展开' : '最小化'" :aria-label="minimized ? '展开' : '最小化'">
              {{ minimized ? '▢' : '—' }}
            </button>
            <button class="icon-btn close-btn" @click="closeWindow" title="关闭" aria-label="关闭">
              ✕
            </button>
          </div>
        </div>

        <Transition name="expand">
          <div v-show="!minimized" class="panel-body">
            <div v-if="userLoaded && !isLoggedIn" class="auth-guard">
              <div class="auth-icon">🔒</div>
              <h3 class="auth-title">登录后使用AI助手</h3>
              <p class="auth-desc">
                为了提供更准确的个性化推荐和保护你的对话记录，
                需要先登录或注册账号后才能使用AI智能语音小助手。
              </p>
              <div class="auth-actions">
                <button class="auth-btn auth-btn-primary" @click="goLogin">
                  立即登录
                </button>
                <button class="auth-btn auth-btn-secondary" @click="goRegister">
                  注册账号
                </button>
              </div>
              <p class="auth-tip">
                ✨ 登录后还能同步你的观影记录、评分历史、收藏，获得更精准的个性化推荐
              </p>
            </div>

            <div v-if="configError" class="config-error">
              <div class="error-icon">⚠️</div>
              <div class="error-text" v-html="configError.replace(/\n/g, '<br>')"></div>
            </div>

            <div ref="chatContainer" class="chat-messages" :class="{ 'is-blurred': userLoaded && !isLoggedIn }">
              <div
                v-for="(msg, idx) in messages"
                :key="idx"
                class="msg-row"
                :class="{ 'is-user': msg.role === 'user', 'is-assistant': msg.role === 'assistant', 'is-error': msg.isError, 'is-welcome': msg.isWelcome }"
              >
                <div class="msg-avatar">{{ msg.role === 'user' ? '👤' : '🎬' }}</div>
                <div class="msg-bubble">
                  <div class="msg-content">
                    <template v-if="msg.role === 'assistant' && !msg.isError && !msg.isWelcome">
                      <template v-for="(seg, segIdx) in getRenderSegments(msg)" :key="segIdx">
                        <span v-if="seg.kind === 'text'" class="msg-text-seg">{{ seg.value }}</span>
                        <router-link
                          v-else-if="seg.kind === 'movie-link' && seg.movie_id"
                          :to="{ name: 'movie-detail', params: { id: Number(seg.movie_id) } }"
                          class="movie-link"
                          :title="'点击查看《' + (seg.title || seg.value) + '》详情页'"
                        >{{ seg.value }}</router-link>
                        <span v-else class="msg-text-seg movie-link-fallback" :title="'《' + (seg.title || seg.value) + '》暂未匹配到详情页'">{{ seg.value }}</span>
                      </template>
                    </template>
                    <template v-else>
                      {{ msg.content }}
                    </template>
                  </div>
                  <div v-if="msg.role === 'assistant' && !msg.isWelcome && !msg.isError" class="msg-actions">
                    <button class="msg-action-btn" @click="speak(msg.content)" :disabled="isSpeaking || !isLoggedIn" title="朗读" aria-label="朗读">
                      {{ isSpeaking ? '🔊' : '🔈' }}
                    </button>
                    <button v-if="isSpeaking" class="msg-action-btn" @click="stopSpeaking" title="停止朗读" aria-label="停止朗读">
                      ⏹
                    </button>
                  </div>
                </div>
              </div>

              <div v-if="isLoading" class="msg-row is-assistant">
                <div class="msg-avatar">🎬</div>
                <div class="msg-bubble">
                  <div class="typing-indicator">
                    <span></span><span></span><span></span>
                  </div>
                </div>
              </div>
            </div>

            <div class="input-area" :class="{ 'is-blurred': userLoaded && !isLoggedIn }">
              <button
                class="voice-btn"
                :class="{ active: isRecording, disabled: !recognition }"
                @click="toggleRecording"
                :title="recognition ? (isRecording ? '停止录音' : '语音输入') : '浏览器不支持语音识别'"
                :aria-label="recognition ? (isRecording ? '停止录音' : '语音输入') : '浏览器不支持语音识别'"
                :disabled="userLoaded && !isLoggedIn"
              >
                {{ isRecording ? '⏺' : '🎤' }}
              </button>
              <textarea
                ref="inputRef"
                v-model="inputText"
                class="msg-input"
                :placeholder="userLoaded && !isLoggedIn ? '请先登录后再输入...' : '输入消息或点击🎤语音提问...'"
                rows="1"
                @keydown="handleKeydown"
                :disabled="isLoading || (userLoaded && !isLoggedIn)"
                :readonly="userLoaded && !isLoggedIn"
                @focus="userLoaded && !isLoggedIn && goLogin()"
              />
              <button
                class="send-btn"
                :disabled="!inputText.trim() || isLoading || (userLoaded && !isLoggedIn)"
                @click="sendMessage"
                title="发送 (Enter)"
                aria-label="发送"
              >
                {{ isLoading ? '…' : '➤' }}
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.ai-assistant-root {
  position: fixed;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC',
    'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
}

.fab-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px 12px 16px;
  border-radius: 999px;
  border: none;
  cursor: pointer;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-size: 14px;
  font-weight: 600;
  box-shadow: 0 8px 28px rgba(102, 126, 234, 0.45), 0 2px 8px rgba(0, 0, 0, 0.12);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.fab-btn:hover {
  transform: translateY(-2px) scale(1.03);
  box-shadow: 0 12px 32px rgba(102, 126, 234, 0.55), 0 4px 12px rgba(0, 0, 0, 0.15);
}

.fab-icon {
  font-size: 20px;
  line-height: 1;
}

.fab-label {
  letter-spacing: 0.3px;
}

.ai-panel {
  width: 380px;
  max-width: calc(100vw - 48px);
  background: var(--card, #ffffff);
  border-radius: 18px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.22), 0 2px 10px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  border: 1px solid var(--border, rgba(0, 0, 0, 0.08));
  backdrop-filter: saturate(180%) blur(20px);
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-radius 0.2s ease;
  transform-origin: center center;
}

.ai-panel.is-minimized {
  width: 300px;
}

.ai-panel.is-dragging {
  transform: scale(1.02);
  box-shadow: 0 32px 80px rgba(102, 126, 234, 0.45), 0 8px 24px rgba(0, 0, 0, 0.18);
  border-radius: 20px;
  transition: transform 0.08s ease, box-shadow 0.08s ease;
  cursor: grabbing;
}

.ai-panel.is-dragging .panel-header,
.ai-panel.is-dragging .panel-body {
  pointer-events: none;
}

[data-theme='dark'] .ai-panel {
  background: var(--card, #1e1f24);
  border-color: var(--border, rgba(255, 255, 255, 0.1));
}

[data-theme='dark'] .ai-panel.is-dragging {
  box-shadow: 0 32px 80px rgba(102, 126, 234, 0.55), 0 8px 24px rgba(0, 0, 0, 0.35);
}

.panel-header {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  user-select: none;
}

.panel-header.is-draggable {
  cursor: grab;
  touch-action: none;
}

.panel-header.is-draggable::before {
  content: '';
  position: absolute;
  left: 50%;
  top: 6px;
  transform: translateX(-50%);
  width: 36px;
  height: 4px;
  border-radius: 2px;
  background: rgba(255, 255, 255, 0.35);
  opacity: 0;
  transition: opacity 0.2s ease;
  pointer-events: none;
}

.panel-header.is-draggable:hover::before {
  opacity: 1;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
  backdrop-filter: blur(4px);
}

.titles {
  min-width: 0;
  flex: 1;
}

.title {
  font-size: 14px;
  font-weight: 700;
  line-height: 1.2;
}

.subtitle {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 3px;
  font-size: 11px;
  opacity: 0.92;
}

.model-tag {
  background: rgba(255, 255, 255, 0.22);
  padding: 1px 7px;
  border-radius: 4px;
  font-family: 'SF Mono', Consolas, monospace;
  font-size: 10.5px;
}

.status.status-ok {
  color: #a7f3d0;
}

.status.status-warn {
  color: #fde68a;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  margin-left: 8px;
}

.icon-btn {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  border: none;
  background: rgba(255, 255, 255, 0.12);
  color: white;
  cursor: pointer;
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s ease;
}

.icon-btn:hover {
  background: rgba(255, 255, 255, 0.25);
}

.icon-btn.close-btn:hover {
  background: rgba(239, 68, 68, 0.7);
}

.panel-body {
  display: flex;
  flex-direction: column;
  height: 480px;
  max-height: calc(100vh - 200px);
}

.config-error {
  display: flex;
  gap: 10px;
  padding: 12px 14px;
  margin: 12px 14px 0;
  background: rgba(251, 191, 36, 0.12);
  border: 1px solid rgba(251, 191, 36, 0.3);
  border-radius: 10px;
  font-size: 12.5px;
  line-height: 1.55;
  color: var(--foreground, #111827);
}

[data-theme='dark'] .config-error {
  color: var(--foreground, #f3f4f6);
}

.error-icon {
  flex-shrink: 0;
  font-size: 16px;
  line-height: 1.4;
}

.error-text {
  flex: 1;
  word-break: break-word;
}

.error-text a {
  color: #2563eb;
  text-decoration: underline;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  scroll-behavior: smooth;
}

.chat-messages::-webkit-scrollbar {
  width: 6px;
}
.chat-messages::-webkit-scrollbar-thumb {
  background: rgba(128, 128, 128, 0.3);
  border-radius: 3px;
}

.msg-row {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  animation: msg-in 0.25s ease-out;
}

@keyframes msg-in {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.msg-row.is-user {
  flex-direction: row-reverse;
}

.msg-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
  background: var(--secondary, #f3f4f6);
  border: 1px solid var(--border, rgba(0, 0, 0, 0.06));
}

.msg-row.is-user .msg-avatar {
  background: linear-gradient(135deg, #60a5fa, #6366f1);
  color: white;
  border-color: transparent;
}

.msg-bubble {
  max-width: calc(100% - 42px);
  min-width: 0;
}

.msg-content {
  padding: 9px 13px;
  border-radius: 12px;
  font-size: 13.5px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  background: var(--secondary, #f3f4f6);
  color: var(--foreground, #111827);
  border-top-left-radius: 4px;
}

.msg-text-seg {
  white-space: pre-wrap;
  word-break: break-word;
}

/* 电影超链接样式 - scoped下必须用:deep()穿透router-link渲染的<a>元素 */
.msg-content :deep(a.movie-link),
.msg-content :deep(.movie-link) {
  display: inline;
  font-weight: 600;
  color: #3b5bdb !important;
  text-decoration: underline !important;
  text-decoration-color: rgba(59, 91, 219, 0.55);
  text-underline-offset: 2.5px;
  padding: 0 2px;
  margin: 0 1px;
  border-radius: 3px;
  background: rgba(59, 91, 219, 0.06);
  cursor: pointer;
  transition: all 0.15s ease;
  word-break: keep-all;
}

.msg-content :deep(a.movie-link):hover,
.msg-content :deep(.movie-link):hover,
.msg-content :deep(a.movie-link):focus-visible,
.msg-content :deep(.movie-link):focus-visible {
  color: #2237a8 !important;
  background: rgba(59, 91, 219, 0.16);
  text-decoration-color: #2237a8 !important;
  text-decoration: underline !important;
  outline: none;
}

.msg-content :deep(a.movie-link):active,
.msg-content :deep(.movie-link):active {
  background: rgba(59, 91, 219, 0.26);
  transform: translateY(0.5px);
}

[data-theme='dark'] .msg-content :deep(a.movie-link),
[data-theme='dark'] .msg-content :deep(.movie-link) {
  color: #91a7ff !important;
  background: rgba(129, 140, 248, 0.16);
  text-decoration-color: rgba(165, 180, 252, 0.7) !important;
}
[data-theme='dark'] .msg-content :deep(a.movie-link):hover,
[data-theme='dark'] .msg-content :deep(.movie-link):hover,
[data-theme='dark'] .msg-content :deep(a.movie-link):focus-visible,
[data-theme='dark'] .msg-content :deep(.movie-link):focus-visible {
  color: #dbe4ff !important;
  background: rgba(129, 140, 248, 0.3);
  text-decoration-color: #dbe4ff !important;
}

/* 触屏设备移除hover，改用点击态保持可识别 */
@media (hover: none) and (pointer: coarse) {
  .msg-content :deep(a.movie-link),
  .msg-content :deep(.movie-link) {
    text-decoration: underline !important;
    text-decoration-thickness: 1.5px;
    background: rgba(59, 91, 219, 0.1);
  }
  .msg-content :deep(a.movie-link):active,
  .msg-content :deep(.movie-link):active {
    background: rgba(59, 91, 219, 0.3);
  }
}

/* 前端兜底识别：暂未匹配到movie_id时显示的fallback样式（仍然是下划线蓝色，只是略灰） */
.msg-content .movie-link-fallback {
  display: inline;
  font-weight: 600;
  color: #5c7cfa;
  text-decoration: underline;
  text-decoration-color: rgba(92, 124, 250, 0.5);
  text-underline-offset: 2.5px;
  padding: 0 2px;
  margin: 0 1px;
  border-radius: 3px;
  background: rgba(92, 124, 250, 0.05);
  word-break: keep-all;
  cursor: help;
  opacity: 0.9;
}

[data-theme='dark'] .msg-content .movie-link-fallback {
  color: #a5b4fc;
  background: rgba(129, 140, 248, 0.1);
  text-decoration-color: rgba(165, 180, 252, 0.5);
}

[data-theme='dark'] .msg-content {
  background: var(--secondary, #2d2e34);
}

.msg-row.is-user .msg-content {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-top-left-radius: 12px;
  border-top-right-radius: 4px;
}

.msg-row.is-error .msg-content {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.25);
  color: inherit;
}

.msg-row.is-welcome .msg-content {
  background: rgba(102, 126, 234, 0.08);
  border: 1px dashed rgba(102, 126, 234, 0.35);
}

.msg-actions {
  display: flex;
  gap: 4px;
  margin-top: 4px;
}

.msg-action-btn {
  padding: 3px 7px;
  font-size: 12px;
  border-radius: 6px;
  border: 1px solid var(--border, rgba(0, 0, 0, 0.08));
  background: transparent;
  color: var(--muted-foreground, #6b7280);
  cursor: pointer;
  transition: all 0.15s ease;
}

.msg-action-btn:hover:not(:disabled) {
  background: var(--secondary, #f3f4f6);
  color: var(--foreground, #111827);
}

.msg-action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 12px 10px;
}

.typing-indicator span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--muted-foreground, #9ca3af);
  opacity: 0.5;
  animation: typing 1.2s infinite ease-in-out;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.15s;
}
.typing-indicator span:nth-child(3) {
  animation-delay: 0.3s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  30% {
    transform: translateY(-5px);
    opacity: 1;
  }
}

.input-area {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 10px 12px 14px;
  border-top: 1px solid var(--border, rgba(0, 0, 0, 0.06));
  background: var(--background, #fafafa);
}

[data-theme='dark'] .input-area {
  background: var(--card, #1e1f24);
}

.voice-btn,
.send-btn {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  border: none;
  cursor: pointer;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.15s ease;
}

.voice-btn {
  background: var(--secondary, #f3f4f6);
  color: var(--foreground, #111827);
  border: 1px solid var(--border, rgba(0, 0, 0, 0.06));
}

.voice-btn:hover:not(.disabled) {
  background: rgba(102, 126, 234, 0.12);
  color: #667eea;
}

.voice-btn.active {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
  animation: pulse-rec 1.2s infinite;
}

@keyframes pulse-rec {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.5);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(239, 68, 68, 0);
  }
}

.voice-btn.disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.msg-input {
  flex: 1;
  resize: none;
  max-height: 120px;
  min-height: 38px;
  padding: 9px 12px;
  border-radius: 10px;
  border: 1px solid var(--border, rgba(0, 0, 0, 0.1));
  background: var(--card, #ffffff);
  color: var(--foreground, #111827);
  font-size: 13.5px;
  line-height: 1.5;
  font-family: inherit;
  outline: none;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

[data-theme='dark'] .msg-input {
  background: #141518;
}

.msg-input:focus {
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.15);
}

.msg-input:disabled {
  opacity: 0.6;
}

.send-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-size: 15px;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
}

.send-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  transform: none;
}

.auth-guard {
  position: relative;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 28px 22px 22px;
  margin: 12px 14px 0;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.12), rgba(118, 75, 162, 0.1));
  border: 1.5px dashed rgba(102, 126, 234, 0.55);
  border-radius: 14px;
  text-align: center;
  animation: auth-in 0.35s ease-out;
}

@keyframes auth-in {
  from { opacity: 0; transform: translateY(-6px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.auth-icon {
  width: 54px;
  height: 54px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: white;
  box-shadow: 0 6px 18px rgba(102, 126, 234, 0.35);
}

.auth-title {
  margin: 4px 0 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--foreground, #111827);
}

.auth-desc {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--muted-foreground, #6b7280);
  max-width: 280px;
}

.auth-actions {
  display: flex;
  gap: 10px;
  margin-top: 4px;
}

.auth-btn {
  padding: 9px 20px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.18s ease;
  border: none;
  font-family: inherit;
}

.auth-btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.35);
}

.auth-btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(102, 126, 234, 0.5);
}

.auth-btn-secondary {
  background: var(--secondary, #f3f4f6);
  color: var(--foreground, #111827);
  border: 1px solid var(--border, rgba(0, 0, 0, 0.08));
}

.auth-btn-secondary:hover {
  background: rgba(102, 126, 234, 0.12);
  color: #667eea;
  border-color: rgba(102, 126, 234, 0.3);
}

.auth-tip {
  margin: 2px 0 0;
  font-size: 11.5px;
  color: #667eea;
  opacity: 0.88;
}

.is-blurred {
  filter: blur(2px);
  pointer-events: none;
  opacity: 0.55;
  user-select: none;
}

/* Transitions */
.fab-pop-enter-active,
.fab-pop-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.fab-pop-enter-from,
.fab-pop-leave-to {
  opacity: 0;
  transform: scale(0.85) translateY(10px);
}

.panel-slide-enter-active,
.panel-slide-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.panel-slide-enter-from,
.panel-slide-leave-to {
  opacity: 0;
  transform: translateY(20px) scale(0.96);
  transform-origin: bottom right;
}

.expand-enter-active,
.expand-leave-active {
  transition: opacity 0.2s ease, max-height 0.25s ease;
  overflow: hidden;
}
.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0 !important;
}

@media (max-width: 640px) {
  .ai-panel {
    width: calc(100vw - 24px);
  }
  .ai-panel.is-minimized {
    width: 260px;
  }
  .panel-body {
    height: 420px;
  }
}
</style>
