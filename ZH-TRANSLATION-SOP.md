# 中文翻译 SOP — 双语页面的 `lang-zh` 文案规范

> 适用：全站所有 `<span class="lang-zh">` 文案（`news.html`、`work.html`、`invited-talks.html`、
> 各篇 blog 的中文版等）。基准范例：`news.html`（2026-08 全表中译定稿）。

## 机制（写文案前先知道这一点）

- 每条内容成对出现，且必须是**兄弟节点**：
  ```html
  <span class="lang-en">Fifteen years of formal methods at AWS</span>
  <span class="lang-zh" hidden>亚马逊云科技形式化方法的十五年</span>
  ```
- 切换由 `assets/js/shell.js` 的 `applyLanguage()` 负责：`.lang-zh` 默认 `hidden`，切到中文时显示；
  **没有配对 `.lang-zh` 的英文会继续显示**，所以漏译不会留白，但也不会被发现——靠本文的 checklist 兜住。
- 中文文案里的链接、`target="_blank" rel="noopener"`、`<small>` 结构一律照抄英文行，只换文字。

## 品牌与专有名词（硬性规则）

| 英文 | 中文 | 说明 |
|---|---|---|
| **AWS / Amazon Web Services（作为公司）** | **亚马逊云科技** | 官方中文名。主语、雇主、单位、职位前缀都算公司名 |
| Amazon（母公司） | 亚马逊 | 与上一条区分：`Amazon` 不等于 `AWS` |
| `AWS <产品>`（AWS Lambda / AWS Fargate / AWS App Runner…） | 原样保留英文 | 产品名整体是商标，不拆开翻译 |
| `Amazon <产品>`（Amazon S3 / Amazon EKS / Amazon Bedrock…） | 原样保留英文 | 同上 |
| 刊物 / 专栏 / 活动的固有名称（AWS Week in Review、AWS Pi Day、AWS Open Source News and Updates、AWS Machine Learning blog、AWS × Docker Container Day…） | 原样保留英文 | 这些是标题本身，不是在指代公司 |
| 人名、球队名、会议名（Marc Brooker、Seahawks、KubeCon、USENIX ATC） | 原样保留英文 | 全站既有惯例 |

### 判断"是不是公司名"的一句话测试

把 `AWS` 换成 `Amazon Web Services` 读一遍：

- 读得通、指的是**这家公司**（发布了什么、增长了多少、某人在这里任职、"on AWS"）→ **亚马逊云科技**
- 读不通，因为它其实是**产品名或标题的一部分**（`Amazon Web Services Lambda`？）→ **保留英文**

示例（均取自 `news.html`）：

| 英文原文 | 中文 |
|---|---|
| Baskar Sridharan is VP of AWS AI/ML services and infrastructure | Baskar Sridharan，**亚马逊云科技** AI/ML 服务与基础设施副总裁 |
| Fifteen years of formal methods at AWS | **亚马逊云科技**形式化方法的十五年 |
| why AWS's cloud growth was a standout | 谈**亚马逊云科技**的云业务增长为何格外亮眼 |
| Generative AI **on AWS** | 在**亚马逊云科技**上用生成式 AI 构建 |
| AWS at KubeCon + CloudNativeCon Europe 2023 | **亚马逊云科技**亮相 KubeCon + CloudNativeCon Europe 2023 |
| Celebrating 10 Years of Amazon Web Services | 庆祝**亚马逊云科技**十周年 |
| 10 Years of Serverless with **AWS Lambda** | **AWS Lambda** 与 Amazon ECS：无服务器十年 |
| Happy 5th Birthday **AWS Fargate**! | **AWS Fargate** 五岁生日快乐！ |
| **AWS Week in Review**: April 18, 2022 | **AWS** 一周回顾：2022 年 4 月 18 日 |

## 排版约定

- 中英文之间留一个半角空格：`亚马逊云科技 AI/ML 服务`、`2022 年 4 月 18 日`。
  纯中文相邻则不加空格：`亚马逊云科技发布`、`亚马逊云科技形式化方法的十五年`。
- 标点用中文全角：`，。：（）！`；并列链接之间用 `、`；书名/引语用 `「」`。
- 日期：`March, 2026` → `2026 年 3 月`。
- 数字、型号、缩写（CVPR、AI/ML、S3）保持原样。

## Checklist（改完中文文案后逐项过）

- [ ] 每个 `.lang-zh` 都有紧邻的 `.lang-en` 兄弟节点，链接与属性和英文行一致
- [ ] 公司名一律 `亚马逊云科技`，产品名/刊物名/活动名一律保留英文
- [ ] `Amazon`（母公司）译作 `亚马逊`，没有和 `AWS` 混用
- [ ] 中英文之间有空格，标点为全角
- [ ] 用下面两条命令自查后再提交：

  ```bash
  # 中文行里仍以公司身份出现的 AWS（逐条人工确认是否属于产品/刊物名例外）
  grep -n 'lang-zh' news.html | grep -n 'AWS'

  # 有英文行但缺中文行的条目（数量应两两相等）
  grep -c 'lang-en' news.html; grep -c 'lang-zh' news.html
  ```

- [ ] 本地起 `python3 scripts/serve.py`，切到「中文」目视过一遍改动的段落
