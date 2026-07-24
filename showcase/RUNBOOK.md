# Site Film Runbook — pengandy.com 全站短片制作手册

以后网站内容更新、需要重制/调整短片时，按本手册操作。

---

## 0. 总览

产物链路：

```
网站页面 ──捕获──▶ showcase/shots/*.png ──场景脚本──▶ showcase/index.html（浏览器可播）
                                                        │
                                                        └──渲染──▶ showcase-film.mp4（YouTube 用）
```

| 文件 | 作用 |
|---|---|
| `showcase/index.html` | 短片本体：场景脚本（SCENES）+ 步骤引擎（rAF 补间） |
| `showcase/capture.py` | 基础长图：13 个独立页面整页截图 + 裁边 |
| `showcase/capture_interactions.py` | 交互素材：首页/地图/PNW 双面板宽图、博文长图 |
| `showcase/capture_round3.py` | 地球旋转 10 帧、creativity 等高分节重截、maps 宽图 |
| `showcase/capture_fakescroll.py` | pill 导航页（publications/service）假滚动分区帧 |
| `showcase/render_film.py` | 渲染 1080p60 MP4（CDP screencast + ffmpeg） |

依赖（一次性）：系统 Chrome、`pip3 install --user playwright imageio-ffmpeg pillow`。
无需 Homebrew、无需下载 Playwright 浏览器（走 `channel="chrome"`）。

---

## 1. 启动本地服务器（所有步骤的前提）

```bash
cd ~/workplace/pymhq.github.io
python3 -m http.server 8123 &
curl -s -o /dev/null -w "%{http_code}" http://localhost:8123/index.html   # 应为 200
```

组件（navbar/footer/service-content）通过 fetch 加载，file:// 打不开，必须走服务器。

## 2. 重截页面素材

页面内容变了才需要做，按变化的页面挑对应脚本跑：

```bash
python3 showcase/capture.py               # 常规长页（portfolio/blog/projects/studio 等）
python3 showcase/capture_interactions.py  # home-wide / maps-wide / pnw-wide / blogpost
python3 showcase/capture_round3.py        # globe-XX 旋转帧 / creativity / maps-wide
python3 showcase/capture_fakescroll.py    # pub-N / svc-N（pill 导航帧）
```

截完必须目检（生成缩略图看一遍），重点检查：
- 懒加载媒体是否渲染（空白段 = 没加载）
- 尾部空白/悬空 footer 是否裁干净
- 面板宽图两侧内容是否完整

### 已踩过的坑（重要）

| 坑 | 处置 |
|---|---|
| `loading="lazy"` / `preload="none"` 媒体不渲染 | 临时副本替换为 eager/metadata 再截 |
| 100vh snap 页面（creativity/visitings/首页）拉高窗口会失真 | 注入 CSS 固定每节高度（`min-height:1000px`）或取消 snap 后再截 |
| 长图「内容—巨型空白—悬空 footer」 | 用最大空白带定位裁剪（脚本已内置） |
| headless 真滚动截图有合成器伪影（scrollIntoView/锚点全废） | 用假滚动：`body{top:-Npx}` + TOC `position:fixed` + JS 手动点亮 active pill |
| 分区偏移量测量 | 注入 JS 把 `getBoundingClientRect().top+scrollY` 写进 `document.title`，`--dump-dom` 读出；滚动值 = 偏移 − 130（TOC 高度） |

## 3. 修改短片（场景/文案/交互）

编辑 `showcase/index.html` 顶部的 `SCENES` 数组。步骤 DSL：

```js
{ wait: ms }                        // 停留
{ pan: { y: srcPx|'end', d } }      // 垂直运镜（源图像素坐标）
{ swipe: { panel: 0|1, d } }        // 宽图横滑（面板索引）
{ cursor: { x, y, d } }             // 光标移动（源图像素坐标，箭头尖端对准）
{ click: true }                     // 点击（按压 + 涟漪）
{ goto: { shot, url, cut|fade } }   // 页内跳转（cut=无缝，fade=柔和，默认白闪）
{ scrollTo: { shot, d } }           // 下一屏从底部滑入（滚动跳转感）
{ frames: { shots: [...], dt } }    // 逐帧序列（如地球旋转）
{ cap: { en, zh } }                 // 换字幕
{ ogcard: true }                    // studio og-card 滑入
```

场景级：`shot`（首图）、`url`（地址栏）、`enterFlash`（进场白闪）、`warm: []`（预热素材）。

### 点击坐标测量方法（必须精确）

给截图叠加坐标网格后目测读数：

```python
# 网格间距 50-100px 粗测，10px 细测（4x 放大）
d.line(...); d.text((x+2,2), str(x))
```

规则：
- 坐标一律用 1600 宽源图像素；宽图第二面板 x = 1600 + 面板内偏移
- pan 之后点击：引擎自动做坐标换算，直接填源图坐标即可
- 已测好的常用坐标：navbar Blog(612,28) Books(738,28) Projects(880,28) Services(968,28)；
  pub pills Books(330,85) Papers(422,85) AWS Blogs(525,85) Invited Talks(632,85) Media(880,85)；
  svc pills Organizing(468,85) Program Committee(660,85)；
  主页 About(466,410) Contact(891,454)；maps 翻页箭头(1272,530)、real thing(2065,598)；
  pnw 翻页箭头(1568,500)、罗盘回主页(1628,30)；blog 置顶博文卡(535,950)

## 4. 验证（每次改完必做）

用 headless 在多个虚拟时间点截图目检：

```bash
for t in 8000 30000 60000 90000 120000; do
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
    --window-size=1280,800 --virtual-time-budget=$t \
    --screenshot=/tmp/f_$t.png "http://localhost:8123/showcase/"
done
# 拼成 grid 后目检关键节点：交互动作前后、字幕、跳转
```

注意：改动场景时长后所有后续时间点都会平移，先粗后细定位。

### 引擎层已修的坑（勿回退）

- **不要用 WAAPI**（`el.animate`）：headless 虚拟时间下 `finished` promise 不推进。全部用 rAF 补间（`tween()`）。
- `raf()` 必须保留 40ms setTimeout 兜底：headless 无动画挂起时停发 BeginFrames。
- 光标以箭头尖端对准目标（-4.6,-1.8 偏移），涟漪落在目标点。

## 5. 浏览器预览

```bash
open "http://localhost:8123/showcase/"
```

快捷键：SPACE 暂停 / ←→ 切场景 / R 重播。点击画面 = 暂停（录屏时别点）。

## 6. 渲染 MP4（上传 YouTube）

```bash
python3 -u showcase/render_film.py     # 产出 showcase-film.mp4（约 2.5 分钟实时捕获）
```

- 输出：1920×1080、恒定 60fps、H.264 yuv420p、faststart，直接拖进 YouTube Studio
- 验证：`ffmpeg -i showcase-film.mp4` 看时长/规格 + 抽帧目检各章节
- **不要用 CDP 虚拟时间逐帧截图**：与新版 headless 合成器死锁（已验证不可行）；
  本脚本用 `Page.startScreencast` 实时捕获 + concat demuxer 按时间戳精确合成

## 7. 发布

```bash
git add showcase/ && git commit -m "..." && git push origin main
# 短片上线：https://pengandy.com/showcase/
# MP4 不入库（.gitignore 已排除），上传 YouTube Studio
```

---

## 附：常见改动的最短路径

| 需求 | 操作 |
|---|---|
| 改字幕/顺序/时长 | 只编辑 `SCENES` → 验证 → 渲染 |
| 某页内容更新 | 重跑对应 capture 脚本 → 目检 → （坐标可能变）重测点击坐标 → 验证 → 渲染 |
| 新增页面场景 | capture 截图 → 加 SCENES 条目 → 验证 → 渲染 |
| 换主题色 | 改 `:root { --accent }` 一处 |
| 录屏隐藏提示条 | URL 加 `?record=1` |
