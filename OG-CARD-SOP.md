# OG Card SOP — 博客社交预览图制作流程

> 适用：每篇博客的 Twitter / LinkedIn 预览图（`og:image` / `twitter:image`）。
> 基准范例：`assets/blog/2026/speculativedecoding/og-card.{html,png}`（2026-07 定稿）。

## 设计原则（定稿共识，勿回退）

1. **不写页面标题、不写作者名、不写域名** —— LinkedIn/Twitter 卡片自带标题和域名显示，图里重复即冗余。
2. **图只负责"钩子"**：一句反直觉的大标语（如 `5× faster. / Zero quality loss.`）+ 一行熟面孔名字制造好奇心。不用纯抽象图形（无点击理由），不放装饰性图案（token 图案已否决）。
3. **极简、高级、低调**：白底、大量留白、只有"墨色 + 一点站点蓝"两个颜色层。
4. **风格与文章排版同源**：
   - 大标语：衬线 `Source Serif 4`（Google Fonts），bold，负字距（`letter-spacing: -0.02em`）
   - 副题：系统无衬线，`#3c4148`（不要浅灰，可读性差）
   - 强调色：站点蓝 `#0076df`（仅用于标语中的关键词）
   - 墨色：`#16181d`
   - 不用 "Puget Sound Journal" 字样（已全站弃用）

## 精度要求（硬性）

| 项 | 要求 |
|---|---|
| 逻辑尺寸 | 1200 × 630（社交平台标准比例 1.91:1） |
| 输出分辨率 | **3x = 3600 × 1890**（`--force-device-scale-factor=3`，不要再缩回 1x） |
| 上限 | 边长 ≤ 4096px、体积 ≤ 5MB（平台限制；平色+文字的 PNG 通常 <300KB，无需担心） |
| 格式 | PNG |

## 制作步骤

1. **复制模板**到新文章的资源目录：

   ```bash
   cp assets/blog/2026/speculativedecoding/og-card.html assets/blog/<year>/<slug>/og-card.html
   ```

2. **只改两处文字**（保持其余样式不动）：
   - `<h1>`：大标语两行——第一行带 `class="accent"` 的钩子（数字/反直觉结论优先），第二行墨色补刀
   - `.sub`：`<b>名字</b> · <b>名字</b> — 一句话说清"错过了什么"`

3. **渲染 PNG**（在仓库根目录执行）：

   ```bash
   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
     --headless --disable-gpu \
     --screenshot=assets/blog/<year>/<slug>/og-card.png \
     --window-size=1200,630 --force-device-scale-factor=3 \
     --virtual-time-budget=8000 --hide-scrollbars \
     "file://$PWD/assets/blog/<year>/<slug>/og-card.html"
   ```

   > `--virtual-time-budget=8000` 是为了等 Google Fonts 加载完成，不可省略。

4. **校验**：

   ```bash
   sips -g pixelWidth -g pixelHeight assets/blog/<year>/<slug>/og-card.png
   # 期望输出 3600 / 1890
   ```

   并肉眼检查一遍渲染结果（字体是否为衬线、有无截断）。

5. **接线**：文章 `index.html` 头部两处 meta 指向绝对 URL：

   ```html
   <meta property="og:image" content="https://pengandy.com/assets/blog/<year>/<slug>/og-card.png">
   <meta name="twitter:image" content="https://pengandy.com/assets/blog/<year>/<slug>/og-card.png">
   ```

6. **提交**：`og-card.html`（设计稿留档）+ `og-card.png` + meta 改动一起 commit。

7. **发布后**：发 LinkedIn 前用 [Post Inspector](https://www.linkedin.com/post-inspector/) 跑一遍文章 URL——既强制刷新平台缓存，也预检真实卡片效果。

## Checklist（发布前逐项过）

- [ ] 图中没有页面标题 / 作者名 / 域名 / "Puget Sound Journal"
- [ ] 钩子是具体的数字或反直觉结论，不是泛泛形容词
- [ ] 只有墨色 + 站点蓝两个颜色层；副题为 `#3c4148` 而非浅灰
- [ ] 输出为 3600 × 1890 PNG，< 5MB
- [ ] meta 为绝对 URL（https://pengandy.com/...）
- [ ] Post Inspector 验证通过
