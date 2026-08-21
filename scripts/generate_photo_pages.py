#!/usr/bin/env python3
"""Generate the photograph collection pages under /photos.

Why this exists
---------------
The collection grew from ten frames to fifty in three sittings, and every
addition touched the same four things: the frames themselves, the per-year
count in each section heading, the census at the top of the page, and the count
advertised on /photos. Hand-editing those in HTML got one of them wrong within
the first round, which is exactly the class of defect scripts/check_site.py was
written for.

So the occasions live here instead, and the page is generated:

  * COLLECTIONS lists the pages; each names its own table, newest year first
  * frame dimensions are read off the built WebP files, never typed, so the
    width, height and every srcset w descriptor state what the file actually is
  * the census and the /photos count are derived from the table, so they cannot
    drift from what is on the page

Run scripts/build_photo_derivatives.py first: it writes the files this reads.

    python3 scripts/generate_photo_pages.py           # write
    python3 scripts/generate_photo_pages.py --check   # exit 1 if stale

Editing rules
-------------
A date is printed only where there is evidence: EXIF DateTimeOriginal, a
filename carrying the day, or a published schedule. Where a camera clock is not
trustworthy the month is printed alone.

Captions carry facts about the occasion and credits name people. Neither
describes the page: an earlier pass annotated frames with remarks like "credited
beneath it", which is scaffolding a reader has no use for.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from collections import defaultdict

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    sys.exit("Pillow is required: python3 -m pip install Pillow")

ROOT = pathlib.Path(__file__).resolve().parent.parent
HUB = ROOT / "photos" / "index.html"


# A frame renders at about 352 CSS px in the three-column flow, 528 in the
# two-column one and 680 on its own; the sheet's column count follows the number
# of frames, so the sizes hint has to as well.
SIZES = {
    1: "(min-width: 780px) 680px, 92vw",
    2: "(min-width: 1024px) 528px, (min-width: 700px) 45vw, 92vw",
    3: ("(min-width: 1280px) 352px, (min-width: 1024px) 30vw, "
        "(min-width: 700px) 45vw, 92vw"),
}

# Reusable credit lines. A credit names a person: who took the frame, or who
# is in it. It is not a place for remarks about the page itself.
HAGEN = ("Photograph by Matt Hagen", "摄影：Matt Hagen")
JM = ("With Jennifer Madriaga (Chief of Staff, The Linux Foundation)",
      "与 Jennifer Madriaga（Linux 基金会幕僚长）")
HANNA = ("With Hanna Hajishirzi (VP, Microsoft AI; Professor, University of "
         "Washington; ex-Senior Director of AI, AI2)",
         "与 Hanna Hajishirzi（微软 AI 副总裁；华盛顿大学教授；前 AI2 "
         "人工智能高级总监）")
# The sponsored students are the group shot, not the two-person one. Vision
# counts seven faces in -c and two in -b, which is how that got settled.
UW_SPONSORED = ("Group photo at the venue with the University of Washington "
                "students I sponsored to attend",
                "会场合影：与我赞助参会的华盛顿大学学生")
# KubeCon EU 2023. The -d frame is CNCF's own photograph, released under
# CC BY-NC-SA 2.0, so the attribution and the licence are a condition of using
# it rather than a courtesy.
# Her own site describes her as "founder of the Cloud Native London meetup" and
# names no employer; the CEO title and the two previous roles are as the owner
# gave them. Both previous roles are read as past, which is how the site reads.
CHERYL = ('With <a href="https://www.oicheryl.com/" target="_blank" '
          'rel="noopener">Cheryl Hung</a> (founder and CEO, Cloud Native London; '
          "previously VP at the Linux Foundation for CNCF, and Senior Director "
          "at Arm)",
          '与 <a href="https://www.oicheryl.com/" target="_blank" '
          'rel="noopener">Cheryl Hung</a>（Cloud Native London 创始人兼 CEO；'
          "此前任 Linux 基金会 CNCF 副总裁、Arm 高级总监）")
# A caption, not a credit: it says what the photograph is of.
MENU = ("On the menu: the EC2 Elastic Cloud Cheeseburger, the Lambda Gyro, the "
        "Bedrock Surprise, S3 Fries, and the EKS Milkshake",
        "菜单：EC2 弹性云芝士汉堡、Lambda 希腊卷饼、Bedrock 惊喜、S3 薯条、EKS 奶昔",
        "f-caption")
CNCF_AMB = ('The CNCF Ambassadors · photograph by the <a '
            'href="https://www.flickr.com/photos/143247548@N03/52838044610/" '
            'target="_blank" rel="noopener">Cloud Native Computing Foundation</a>, '
            '<a href="https://creativecommons.org/licenses/by-nc-sa/2.0/" '
            'target="_blank" rel="noopener">CC BY-NC-SA 2.0</a>',
            'CNCF Ambassador 合影 · 摄影：<a '
            'href="https://www.flickr.com/photos/143247548@N03/52838044610/" '
            'target="_blank" rel="noopener">Cloud Native Computing Foundation</a>，'
            '<a href="https://creativecommons.org/licenses/by-nc-sa/2.0/" '
            'target="_blank" rel="noopener">CC BY-NC-SA 2.0</a> 许可')
CHRIS = ("Chris Aniszczyk (VP, Developer Relations, the Linux Foundation; CTO, "
         "CNCF) announcing the new Ambassadors at the opening",
         "Chris Aniszczyk（Linux 基金会开发者关系副总裁；CNCF CTO）在开场上公布新一届 Ambassador")
ALOLITA = ("With Alolita Sharma (then Senior Manager, Software Engineering and "
           "Principal Technologist, AWS, and concurrently a CNCF Governing Board "
           "member, Chair of the End User TAB and Co-chair of the Observability "
           "TAG; now Engineering Management, Observability and Platform "
           "Technologies, Apple) and Michael Hausenblas (then Principal Product "
           "Manager, AWS; now Principal Software Engineer, Genesys)",
           "与 Alolita Sharma（时任亚马逊云科技软件工程高级经理与首席技术专家，同时是 "
           "CNCF 董事会成员、End User TAB 主席、Observability TAG 联合主席；现于 Apple "
           "负责可观测性与平台技术的工程管理）、Michael Hausenblas（时任亚马逊云科技首席"
           "产品经理；现为 Genesys 首席软件工程师）")
KNATIVE = ("With the Knative group", "与 Knative 团队")
ANNI = ("With Anni Lai (General Member Representative and Generative AI Commons "
        "Co-chair, LF AI &amp; Data; Head of Open Source Operations and Marketing, "
        "Futurewei)",
        "与 Anni Lai（LF AI &amp; Data 普通会员代表、Generative AI Commons 联合主席；"
        "Futurewei 开源运营与市场负责人）")
AWSTEAM = ("With the AWS team", "与亚马逊云科技的同事们")
BARRY = ("With Barry Cooks (VP, AWS Compute Abstractions; CNCF Governing Board "
         "member)",
         "与 Barry Cooks（亚马逊云科技 Compute Abstractions 副总裁；CNCF 董事会成员）")
KEVIN = ("With Kevin (Zefeng) Wang (Vice Chair of the CNCF Technical Oversight "
         "Committee and a CNCF Ambassador; Lead of the Cloud Native Open Source "
         "Team, Huawei)",
         "与 Kevin (Zefeng) Wang（CNCF 技术监督委员会副主席、CNCF Ambassador；"
         "华为云原生开源团队负责人）")
MATT = ("With Matt White (Global CTO of AI, the Linux Foundation; CTO, the "
        "PyTorch Foundation)",
        "与 Matt White（Linux 基金会全球 AI CTO；PyTorch 基金会 CTO）")
TIM = ("With Tim Hockin (Distinguished Software Engineer, Google Cloud: "
       "Kubernetes and GKE)",
       "与 Tim Hockin（Google Cloud 杰出软件工程师，负责 Kubernetes 与 GKE）")
JANET = ("With Janet Kuo (Staff Software Engineer, Google Cloud)",
         "与 Janet Kuo（Google Cloud 资深软件工程师）")
KATIE = ("With Katie Greenley (Senior Manager, Marketing and Community, CNCF, "
         "the Linux Foundation; Marketing Committee Co-chair)",
         "与 Katie Greenley（Linux 基金会 CNCF 市场与社区高级经理；市场委员会联合主席）")
KELSEY = ("With Kelsey Hightower (Distinguished Software Engineer)",
          "与 Kelsey Hightower（杰出软件工程师）")
BRIAN = ("With Brian Grant (Distinguished Software Engineer, Google)",
         "与 Brian Grant（谷歌杰出软件工程师）")
ROLANDA = ('With <a href="https://www.madrona.com/team-profiles/rolanda-fu/" '
           'target="_blank" rel="noopener">Rolanda Fu</a> (Investor, Madrona) and '
           'Anna Hong (CEO and Co-founder, B.E.L.L.E.)',
           '与 <a href="https://www.madrona.com/team-profiles/rolanda-fu/" '
           'target="_blank" rel="noopener">Rolanda Fu</a>（Madrona 投资人）、'
           'Anna Hong（B.E.L.L.E. 联合创始人 & CEO）')
JAY = ("With Jay Bartot (Technical Partner, Madrona Venture Labs; Affiliate "
       "Professor, University of Washington)",
       "与 Jay Bartot（Madrona Venture Labs 技术合伙人；华盛顿大学客座教授）")

# Count words for the section headings, so the heading cannot disagree with the
# number of frames under it.
ADAM = ("With Adam Selipsky, then CEO of AWS", "与时任亚马逊云科技 CEO 的 Adam Selipsky")
DEEPAK = ("With Deepak Singh, then Vice President for Developers, Events, "
          "Containers and Serverless, now VP, AWS Agentic AI",
          "与 Deepak Singh，时任开发者、活动、容器与 Serverless 副总裁，"
          "现任亚马逊云科技 Agentic AI 副总裁")
JAMES = ('With <a href="https://www.wired.com/2013/02/james-hamilton-amazon/" '
         'target="_blank" rel="noopener">James Hamilton</a>, SVP and '
         'Distinguished Engineer, Amazon',
         '与 <a href="https://www.wired.com/2013/02/james-hamilton-amazon/" '
         'target="_blank" rel="noopener">James Hamilton</a>，亚马逊高级副总裁'
         '兼杰出工程师')
# The parenthetical keeps the earlier teams out of the way of
# check_photo_credits.py, which would otherwise read "and Observability" as a
# second person and demand a second face.
#
# The current role is as the owner gave it. The linked AWS page is older: it
# still lists Monitoring and Observability as current and says Engineer rather
# than Technologist. It does corroborate the Lambda and Observability history.
DAVID = ('With <a href="https://aws.amazon.com/builders-library/authors/'
         'david-yanacek/" target="_blank" rel="noopener">David Yanacek</a> '
         "(Senior Principal Technologist, Agentic AI Leadership; previously AWS "
         "Monitoring and Observability, AWS Lambda)",
         '与 <a href="https://aws.amazon.com/builders-library/authors/'
         'david-yanacek/" target="_blank" rel="noopener">David Yanacek</a>'
         "（Agentic AI 领导层高级首席技术专家；此前任职于亚马逊云科技监控与可观测性、"
         "AWS Lambda）")
PROSERVE = ("With Junjie Tang (Senior Principal, AWS ProServe) and Desmond (Yi) "
            "Zhou (PXT, Amazon)",
            "与 Junjie Tang（亚马逊云科技专业服务 ProServe 高级首席）、"
            "Desmond (Yi) Zhou（亚马逊 PXT）")
TIANWEI = ('With <a href="https://personal.ntu.edu.sg/tianwei.zhang/" '
           'target="_blank" rel="noopener">Tianwei Zhang</a>, now Associate '
           "Professor and Provost's Chair in Computing at Nanyang "
           'Technological University',
           '与 <a href="https://personal.ntu.edu.sg/tianwei.zhang/" '
           'target="_blank" rel="noopener">Tianwei Zhang</a>，现为南洋理工大学'
           '计算机学院副教授、教务长讲席教授')

_ONES = ("", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight",
         "Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen",
         "Sixteen", "Seventeen", "Eighteen", "Nineteen")
_TENS = ("", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy",
         "Eighty", "Ninety")
_ZH_DIGITS = "零一二三四五六七八九"


def _count_en(n: int) -> str:
    if n < 20:
        return _ONES[n]
    tens, ones = divmod(n, 10)
    return _TENS[tens] + (f"-{_ONES[ones].lower()}" if ones else "")


def _count_zh(n: int) -> str:
    """Chinese numeral for a count of frames.

    A bare two takes 两 before a measure word, but the two inside a compound
    stays 二: 两张, yet 十二张 and 二十二张. Getting this wrong is the kind of
    thing a fixed lookup table hid until the collection outgrew it.
    """
    if n == 2:
        return "两"
    if n < 10:
        return _ZH_DIGITS[n]
    if n < 20:
        return "十" + (_ZH_DIGITS[n % 10] if n % 10 else "")
    tens, ones = divmod(n, 10)
    return _ZH_DIGITS[tens] + "十" + (_ZH_DIGITS[ones] if ones else "")


def count_words(n: int) -> tuple[str, str]:
    """("Thirty-one frames", "三十一张") for the section heading."""
    if not 1 <= n < 100:
        sys.exit(f"count_words has no wording for {n}")
    return (f"{_count_en(n)} frame" + ("" if n == 1 else "s"), f"{_count_zh(n)}张")

EVENTS = [
 ("2026", "Bellevue, Seattle", "Bellevue、西雅图", [
   dict(
     venue_en="Fremont Brewing's Urban Beer Garden · Seattle",
     venue_zh="Fremont Brewing's Urban Beer Garden · 西雅图",
     title_en="The RLHF Book Launch", title_zh="RLHF 新书发布会",
     note_en="Guest · 10 August 2026 · Nathan Lambert's Reinforcement Learning "
             "from Human Feedback · hosted by Nathan Lambert and Mia Ocolisanu, "
             'presented by RadixArk · <a href="https://luma.com/nytpq2x7" '
             'target="_blank" rel="noopener">event page</a>',
     note_zh="嘉宾 · 2026 年 8 月 10 日 · Nathan Lambert 著《人类反馈强化学习》· "
             "主办：Nathan Lambert、Mia Ocolisanu，由 RadixArk 呈现 · "
             '<a href="https://luma.com/nytpq2x7" target="_blank" '
             'rel="noopener">活动页面</a>',
     alt="The RLHF Book Launch for Nathan Lambert's Reinforcement Learning from "
         "Human Feedback, Fremont Brewing's Urban Beer Garden, Seattle, 10 August 2026.",
     frames=[("2026-rlhf-book-launch-a", None), ("2026-rlhf-book-launch-b", None)]),
   dict(
     venue_en="MLSys 2026 · Bellevue", venue_zh="MLSys 2026 · 华盛顿州 Bellevue",
     title_en="Conference on Machine Learning and Systems",
     title_zh="机器学习与系统大会",
     note_en="Guest · 17 to 22 May 2026 · Hyatt Regency Bellevue · lunch with Matt "
             "White, Global CTO of AI at the Linux Foundation and CTO of the "
             "PyTorch Foundation · "
             '<a href="/blog/2026/lunch-with-mattwhite/">the write-up</a>',
     note_zh="嘉宾 · 2026 年 5 月 17 日至 22 日 · Hyatt Regency Bellevue · 与 Linux "
             "基金会全球 AI CTO、PyTorch 基金会 CTO Matt White 的午餐 · "
             '<a href="/blog/2026/lunch-with-mattwhite/">那篇记录</a>',
     alt="MLSys 2026, the Conference on Machine Learning and Systems, Bellevue, Washington.",
     frames=[("2026-mlsys-a", MATT,
              "Andy Peng and Matt White at MLSys 2026, both wearing MLSys lanyards"),
             ("2026-mlsys-b", None)]),
   dict(
     venue_en="University of Washington · MSIS 549", venue_zh="华盛顿大学 · MSIS 549",
     title_en="Machine Learning and Artificial Intelligence for Business Applications",
     title_zh="面向商业应用的机器学习与人工智能",
     note_en='MSIS 549, UW Foster · 14 March 2026 · PACCAR Hall, University of '
             'Washington · hosted by <a href="https://foster.uw.edu/faculty-research/directory/leonard-boussioux/" target="_blank" rel="noopener">Léonard Boussioux</a>',
     note_zh='MSIS 549，华盛顿大学 Foster 商学院 · 2026 年 3 月 14 日 · '
             '华盛顿大学 PACCAR Hall · 邀请人：<a href="https://foster.uw.edu/faculty-research/directory/leonard-boussioux/" target="_blank" rel="noopener">Léonard Boussioux</a>',
     alt="MSIS 549 at the University of Washington, 14 March 2026.",
     frames=[("2026-uw-msis-549-a", None), ("2026-uw-msis-549-b", None),
             ("2026-uw-msis-549-c", None), ("2026-uw-msis-549-d", None),
             ("2026-uw-msis-549-e", None)]),
 ]),
 ("2025", "Mexico City, Vancouver, Seattle, online", "墨西哥城、温哥华、西雅图、线上", [
   dict(
     venue_en="NeurIPS 2025 · Mexico City", venue_zh="NeurIPS 2025 · 墨西哥城",
     title_en="NeurIPS CDMX, the conference's first satellite city",
     title_zh="NeurIPS CDMX：大会首个卫星会场",
     note_en='Workshop Co-Chair · 30 November to 5 December 2025, running in parallel with San Diego · <a href="/blog/2025/neurips/">trip notes</a> · <a href="https://neurips.cc/Conferences/2025/Committees" target="_blank" rel="noopener">committee</a>',
     note_zh='Workshop Co-Chair · 2025 年 11 月 30 日至 12 月 5 日，与圣迭戈会场并行举行 · <a href="/blog/2025/neurips/">行程记录</a> · <a href="https://neurips.cc/Conferences/2025/Committees" target="_blank" rel="noopener">组织委员会</a>',
     alt="NeurIPS CDMX 2025, the conference's Mexico City satellite location.",
     frames=[("2025-neurips-cdmx-a", None), ("2025-neurips-cdmx-b", None),
             ("2025-neurips-cdmx-c", None)]),
   dict(
     venue_en="UW AI &amp; Robotics Data Summit", venue_zh="UW AI &amp; Robotics Data Summit",
     title_en="LLM Native Primitives: Next Golden Path",
     title_zh="LLM 原生原语：下一条黄金路径",
     note_en='Keynote · 28 August 2025 · Boeing Advanced Research Center, University of Washington · hosted by <a href="https://www.me.washington.edu/facultyfinder/xu-chen" target="_blank" rel="noopener">Xu Chen</a> · <a href="https://luma.com/iqjrwcal" target="_blank" rel="noopener">event page</a>',
     note_zh='主旨演讲 · 2025 年 8 月 28 日 · 华盛顿大学波音先进研究中心 · 主办：<a href="https://www.me.washington.edu/facultyfinder/xu-chen" target="_blank" rel="noopener">Xu Chen</a> · <a href="https://luma.com/iqjrwcal" target="_blank" rel="noopener">活动页面</a>',
     alt="UW AI &amp; Robotics Data Summit, Boeing Advanced Research Center, University of Washington, 28 August 2025.",
     frames=[("2025-uw-ai-robotics-summit-a", None), ("2025-uw-ai-robotics-summit-b", None),
             ("2025-uw-ai-robotics-summit-c", None), ("2025-uw-ai-robotics-summit-d", None),
             ("2025-uw-ai-robotics-summit-e", None)]),
   dict(
     venue_en="ICML 2025 · Vancouver", venue_zh="ICML 2025 · 温哥华",
     title_en="International Conference on Machine Learning",
     title_zh="国际机器学习大会",
     note_en='Reviewer · July 2025 · Vancouver Convention Centre · <a href="/blog/2025/icml/">recap</a>',
     note_zh='审稿人 · 2025 年 7 月 · 温哥华会议中心 · <a href="/blog/2025/icml/">小结</a>',
     alt="ICML 2025 at the Vancouver Convention Centre.",
     frames=[("2025-icml-yvr-a", None), ("2025-icml-yvr-b", None),
             ("2025-icml-yvr-c", None)]),
   dict(
     venue_en="FlickBloom Tech Talks · Seattle", venue_zh="FlickBloom Tech Talks · 西雅图",
     title_en="Consumer-facing AI agents evaluation and validation",
     title_zh="面向消费者的 AI Agent 评估与验证",
     note_en="Guest · 19 July 2025 · Foundations, Seattle · talk by Dr. Zhou (Jo) Yu "
             "(Professor of Computer Science, Columbia University; Founder &amp; CEO, "
             "Arklex.ai; Forbes 30 Under 30, 2018) · "
             '<a href="https://luma.com/t73dw8af" target="_blank" rel="noopener">event page</a>',
     note_zh="嘉宾 · 2025 年 7 月 19 日 · Foundations，西雅图 · 主讲：Dr. Zhou (Jo) Yu"
             "（哥伦比亚大学计算机科学教授；Arklex.ai 创始人 &amp; CEO；2018 年福布斯 "
             "30 Under 30）· "
             '<a href="https://luma.com/t73dw8af" target="_blank" rel="noopener">活动页面</a>',
     alt="FlickBloom tech talk on evaluating consumer-facing AI agents, Foundations, Seattle, 19 July 2025.",
     frames=[("2025-flickbloom-agents", None)]),
   dict(
     venue_en="Packt GenAI Summit", venue_zh="Packt GenAI Summit",
     title_en="State of Open Source LLM", title_zh="开源大语言模型现状",
     note_en='Keynote · online · <a href="https://www.linkedin.com/events/deepseekdemystifiedsummit7349071392195104771/" target="_blank" rel="noopener">event page</a>',
     note_zh='主旨演讲 · 线上 · <a href="https://www.linkedin.com/events/deepseekdemystifiedsummit7349071392195104771/" target="_blank" rel="noopener">活动页面</a>',
     alt="Speaker card for the Packt GenAI Summit 2025.",
     frames=[("2025-packt-genai-summit", None)]),
   dict(
     venue_en="University of Washington · Foster MSIS",
     venue_zh="华盛顿大学 · Foster 商学院 MSIS",
     title_en="MSIS Mentorship Celebration", title_zh="MSIS 导师计划庆祝活动",
     note_en="Anthony's Forum, Dempsey Hall, University of Washington · Seattle, "
             "3 June 2025",
     note_zh="华盛顿大学 Dempsey Hall，Anthony's Forum · 西雅图，2025 年 6 月 3 日",
     alt="MSIS Mentorship Celebration at the University of Washington, 3 June 2025.",
     frames=[("2025-msis-mentorship-a", HAGEN), ("2025-msis-mentorship-b", HAGEN),
             ("2025-msis-mentorship-c", HAGEN), ("2025-msis-mentorship-d", None),
             ("2025-msis-mentorship-e", None)]),
   dict(
     venue_en="SMILE · Seattle", venue_zh="SMILE · 西雅图",
     title_en="Succeed in Internal Transfer", title_zh="如何成功完成内部转岗",
     note_en="Seattle Amazonian Chinese League · 27 May 2025",
     note_zh="西雅图亚马逊华人联盟 · 2025 年 5 月 27 日",
     alt="SMILE session on succeeding in an internal transfer, Seattle, 27 May 2025.",
     frames=[("2025-smile-internal-transfer-a", None),
             ("2025-smile-internal-transfer-b", None),
             ("2025-smile-internal-transfer-c", None)]),
 ]),
 ("2024", "Seattle, online", "西雅图、线上", [
   dict(
     venue_en="OnBoard! Podcast · episode artwork",
     venue_zh="OnBoard! 播客 · 单集配图",
     title_en="New Software Development Paradigms in the LLM Era",
     title_zh="LLM 时代需要怎样的软件开发新范式",
     note_en='Panel with Yangqing Jia 贾扬清 and Ed Huang 黄东旭 · moderated by Monica Xie · livestream · <a href="https://www.xiaoyuzhoufm.com/episode/676054e37d8426f6929d67cb?s=eyJ1IjogIjYwYjVhNzYxZTBmNWU3MjNiYjU4ZmNlYSJ9" target="_blank" rel="noopener">podcast</a> · <a href="https://mp.weixin.qq.com/s/wOZknRagMGyp8AluNqAzYg" target="_blank" rel="noopener">transcript</a>',
     note_zh='圆桌，同场：贾扬清、黄东旭 · 主持：Monica Xie · 直播 · <a href="https://www.xiaoyuzhoufm.com/episode/676054e37d8426f6929d67cb?s=eyJ1IjogIjYwYjVhNzYxZTBmNWU3MjNiYjU4ZmNlYSJ9" target="_blank" rel="noopener">播客</a> · <a href="https://mp.weixin.qq.com/s/wOZknRagMGyp8AluNqAzYg" target="_blank" rel="noopener">文字版</a>',
     alt="Episode artwork for the OnBoard! podcast episode on software development in the LLM era.",
     frames=[("2024-onboard-podcast-a", None), ("2024-onboard-podcast-b", None)]),
   dict(
     venue_en="B.E.L.L.E. · Seattle", venue_zh="B.E.L.L.E. · 西雅图",
     title_en="AI, Equity, and Innovations: Shaping the Future of Technology and Venture Capital",
     title_zh="人工智能、公平与创新：塑造科技与风险投资的未来",
     note_en="16 November 2024 · Capital One Café, Seattle",
     note_zh="2024 年 11 月 16 日 · Capital One Café，西雅图",
     alt="B.E.L.L.E. community panel on AI, equity and venture capital, Capital One Café, Seattle, 16 November 2024.",
     frames=[("2024-belle-seattle", ROLANDA)]),
   dict(
     venue_en="China Entrepreneur Network · University of Washington",
     venue_zh="China Entrepreneur Network · 华盛顿大学西雅图分校",
     title_en="Dinner With Professionals (DWP)",
     title_zh="Dinner With Professionals（DWP）",
     note_en='Invited professional · October 2024 · Kane Hall, University of Washington · Seattle · <a href="https://mp.weixin.qq.com/s/7qbcaW5sIsujO6kauIWY8Q" target="_blank" rel="noopener">write-up</a>',
     note_zh='受邀职场嘉宾 · 2024 年 10 月 · 华盛顿大学 Kane Hall · 西雅图 · <a href="https://mp.weixin.qq.com/s/7qbcaW5sIsujO6kauIWY8Q" target="_blank" rel="noopener">活动记录</a>',
     alt="Dinner With Professionals, hosted by the China Entrepreneur Network at the University of Washington, October 2024.",
     frames=[("2024-cen-dwp-a", None), ("2024-cen-dwp-b", None)]),
   dict(
     venue_en="Madrona Venture Group Inc. · Seattle",
     venue_zh="Madrona Venture Group Inc. · 西雅图",
     title_en="OpenAI Community Meetup", title_zh="OpenAI 社区聚会",
     note_en="Guest · 1 August 2024 · DocuSign Tower, Seattle",
     note_zh="嘉宾 · 2024 年 8 月 1 日 · 西雅图 DocuSign Tower",
     alt="OpenAI Community Meetup Seattle at Madrona Venture Group, DocuSign Tower, 1 August 2024.",
     frames=[("2024-openai-meetup-seattle-a", None),
             ("2024-openai-meetup-seattle-b", None),
             ("2024-openai-meetup-seattle-c", JAY)]),
   dict(
     venue_en="SMILE · Seattle", venue_zh="SMILE · 西雅图",
     title_en="GenAI 茶话会", title_zh="GenAI 茶话会",
     note_en='Panel with Xiaopeng Li and Raphael Shu · Seattle Amazonian Chinese League · <a href="https://www.xiaohongshu.com/discovery/item/6688bd8b000000001c0250fe?source=webshare&amp;xhsshare=pc_web&amp;xsec_token=ABKX1wuwAQJwr-A9ZoGU-cldn7AEkGNosdYsdMrzpMeqg=&amp;xsec_source=pc_share" target="_blank" rel="noopener">Rednote post</a>',
     note_zh='圆桌，同场：Xiaopeng Li、Raphael Shu · 西雅图亚马逊华人联盟 · <a href="https://www.xiaohongshu.com/discovery/item/6688bd8b000000001c0250fe?source=webshare&amp;xhsshare=pc_web&amp;xsec_token=ABKX1wuwAQJwr-A9ZoGU-cldn7AEkGNosdYsdMrzpMeqg=&amp;xsec_source=pc_share" target="_blank" rel="noopener">小红书笔记</a>',
     alt="The GenAI panel at SMILE, the Seattle Amazonian Chinese League, 2024.",
     frames=[("2024-smile-genai-panel", None)]),
   dict(
     venue_en="CVPR 2024 · Seattle", venue_zh="CVPR 2024 · 西雅图",
     title_en="Computer Vision and Pattern Recognition",
     title_zh="计算机视觉与模式识别大会",
     note_en="Guest · 17 to 21 June 2024 · Seattle Convention Center",
     note_zh="嘉宾 · 2024 年 6 月 17 日至 21 日 · 西雅图会议中心",
     alt="CVPR 2024, the Computer Vision and Pattern Recognition conference, Seattle Convention Center.",
     frames=[("2024-cvpr-a", None,
              "A CVPR 2024 attendee badge, its QR code blanked."),
             ("2024-cvpr-b", None)]),
   dict(
     venue_en="Google Bay View · Mountain View", venue_zh="谷歌 Bay View 办公室 · 山景城",
     title_en="KuberTENes Birthday Bash", title_zh="KuberTENes 生日会",
     note_en="Guest · 6 June 2024 · ten years of Kubernetes · "
             '<a href="https://events.linuxfoundation.org/kuber10es-birthday-bash/" '
             'target="_blank" rel="noopener">event page</a> · '
             '<a href="/blog/2025/cncf10yo/">my ten KubeCons</a>',
     note_zh="嘉宾 · 2024 年 6 月 6 日 · Kubernetes 十周年 · "
             '<a href="https://events.linuxfoundation.org/kuber10es-birthday-bash/" '
             'target="_blank" rel="noopener">活动页面</a> · '
             '<a href="/blog/2025/cncf10yo/">我的十次 KubeCon</a>',
     alt="KuberTENes Birthday Bash, ten years of Kubernetes, at Google's Bay View office in Mountain View, 6 June 2024.",
     frames=[("2024-kubertenes-a", None), ("2024-kubertenes-b", TIM),
             ("2024-kubertenes-c", JANET), ("2024-kubertenes-d", KATIE),
             ("2024-kubertenes-e", KELSEY), ("2024-kubertenes-f", BRIAN)]),
   dict(
     venue_en="University of Washington · MSIS 549",
     venue_zh="华盛顿大学 · MSIS 549",
     title_en="Transforming AI: Modern Business Redefine",
     title_zh="变革人工智能：重新定义现代商业",
     note_en='Guest lecturer · MSIS 549 (2): Machine Learning and Artificial Intelligence for Business Applications · PACCAR Hall, University of Washington · <a href="https://www.linkedin.com/posts/margaretmz_it-has-been-a-wonderful-experience-teaching-ugcPost-7190422362406735872-K7Bs?utm_source=share&amp;utm_medium=member_desktop" target="_blank" rel="noopener">LinkedIn post</a>',
     note_zh='客座讲师 · MSIS 549（2）：面向商业应用的机器学习与人工智能 · 华盛顿大学 PACCAR Hall · <a href="https://www.linkedin.com/posts/margaretmz_it-has-been-a-wonderful-experience-teaching-ugcPost-7190422362406735872-K7Bs?utm_source=share&amp;utm_medium=member_desktop" target="_blank" rel="noopener">领英帖子</a>',
     alt="Guest lecture for MSIS 549 at the University of Washington, 2024.",
     frames=[("2024-uw-msis-549-a", None), ("2024-uw-msis-549-b", None),
             ("2024-uw-msis-549-c", None), ("2024-uw-msis-549-d", None)]),
   dict(
     venue_en="Open Source Summit North America · Seattle",
     venue_zh="Open Source Summit North America · 西雅图",
     title_en="Open Source Summit North America 2024",
     title_zh="Open Source Summit 北美站 2024",
     note_en="16 to 18 April 2024 · Seattle Convention Center",
     note_zh="2024 年 4 月 16 日至 18 日 · 西雅图会议中心",
     alt="Open Source Summit North America 2024, Seattle Convention Center.",
     frames=[("2024-open-source-summit-na-a", MENU,
              "An AWS-themed food menu at Open Source Summit North America 2024, "
              "its QR code blanked."),
             ("2024-open-source-summit-na-b", HANNA),
             ("2024-open-source-summit-na-c", UW_SPONSORED),
             ("2024-open-source-summit-na-d", None),
             ("2024-open-source-summit-na-e", JM)]),
   dict(
     venue_en="University of Washington · MSIS 547",
     venue_zh="华盛顿大学 · MSIS 547",
     title_en="New Era of Generative AI and Building in the Cloud",
     title_zh="生成式人工智能新时代与云上构建",
     note_en='Guest lecturer · MSIS 547 (2): Managing in the Era of Cloud Computing · 2 March 2024 · PACCAR Hall, University of Washington · co-lecturer Jay Bartot · hosted by <a href="https://foster.uw.edu/faculty-research/directory/leonard-boussioux/" target="_blank" rel="noopener">Léonard Boussioux</a> · <a href="https://www.linkedin.com/posts/uw-foster-msis_msis-genai-demoday-ugcPost-7173432871800483841-wW0C?utm_source=share&amp;utm_medium=member_desktop" target="_blank" rel="noopener">UW Foster MSIS post</a> · <a href="https://www.linkedin.com/posts/leonard-boussioux_forging-ai-champions-a-transformative-ugcPost-7188941809279000576-ZKov?utm_source=share&amp;utm_medium=member_desktop" target="_blank" rel="noopener">LinkedIn post</a>',
     note_zh='客座讲师 · MSIS 547（2）：云计算时代的管理 · 2024 年 3 月 2 日 · 华盛顿大学 PACCAR Hall · 共同讲师：Jay Bartot · 邀请人：<a href="https://foster.uw.edu/faculty-research/directory/leonard-boussioux/" target="_blank" rel="noopener">Léonard Boussioux</a> · <a href="https://www.linkedin.com/posts/uw-foster-msis_msis-genai-demoday-ugcPost-7173432871800483841-wW0C?utm_source=share&amp;utm_medium=member_desktop" target="_blank" rel="noopener">UW Foster MSIS 帖子</a> · <a href="https://www.linkedin.com/posts/leonard-boussioux_forging-ai-champions-a-transformative-ugcPost-7188941809279000576-ZKov?utm_source=share&amp;utm_medium=member_desktop" target="_blank" rel="noopener">领英帖子</a>',
     alt="Guest lecture for MSIS 547 at the University of Washington, 2 March 2024.",
     frames=[("2024-uw-msis-547-a", JAY), ("2024-uw-msis-547-b", None),
             ("2024-uw-msis-547-c", None), ("2024-uw-msis-547-d", None),
             ("2024-uw-msis-547-e", None)]),
 ]),
 ("2023", "Amsterdam, New York, Seattle, online",
          "阿姆斯特丹、纽约、西雅图、线上", [
   dict(
     venue_en="Women in Tech Regatta · Seattle",
     venue_zh="Women in Tech Regatta · 西雅图",
     title_en="Myth-Busting Tech Trends", title_zh="破解科技趋势迷思",
     note_en='Panel with Morgan Zion and Caroline Williams · moderated by Padmaja Vrudhula · April 2023 · <a href="https://seattleregatta2023.sched.com/event/1LEF6/myth-busting-tech-trends-supported-by-northeastern-university" target="_blank" rel="noopener">session page</a>',
     note_zh='圆桌，同场：Morgan Zion、Caroline Williams · 主持：Padmaja Vrudhula · 2023 年 4 月 · <a href="https://seattleregatta2023.sched.com/event/1LEF6/myth-busting-tech-trends-supported-by-northeastern-university" target="_blank" rel="noopener">议程页面</a>',
     alt="The Myth-Busting Tech Trends panel at the Seattle Women in Tech Regatta 2023.",
     frames=[("2023-women-in-tech-regatta-a", None), ("2023-women-in-tech-regatta-b", None),
             ("2023-women-in-tech-regatta-c", None), ("2023-women-in-tech-regatta-d", None)]),
   dict(
     venue_en="KubeCon + CloudNativeCon Europe · Amsterdam",
     venue_zh="KubeCon + CloudNativeCon Europe · 阿姆斯特丹",
     title_en="KubeCon + CloudNativeCon Europe 2023",
     title_zh="KubeCon + CloudNativeCon Europe 2023",
     note_en="Speaker, and announced here as a CNCF Ambassador · 18 to 21 April "
             "2023 · presented \u201cThe open-source community at AWS: containerd "
             "and Envoy\u201d with Phil Estes · "
             '<a href="https://twitter.com/AWSOpen/status/1647989049305575428?s=20" target="_blank" rel="noopener">AWS Open Source post</a> · '
             '<a href="/blog/2025/cncf10yo/">my ten KubeCons</a>',
     note_zh="演讲者，并在会上正式公布为 CNCF Ambassador · 2023 年 4 月 18 日至 21 日 · "
             "与 Phil Estes 共同演讲《亚马逊云科技的开源社区：containerd 与 Envoy》· "
             '<a href="https://twitter.com/AWSOpen/status/1647989049305575428?s=20" target="_blank" rel="noopener">AWS 开源团队动态</a> · '
             '<a href="/blog/2025/cncf10yo/">我的十次 KubeCon</a>',
     alt="KubeCon + CloudNativeCon Europe 2023, Amsterdam.",
     frames=[("2023-kubecon-eu-a", None), ("2023-kubecon-eu-b", None),
             ("2023-kubecon-eu-c", None), ("2023-kubecon-eu-d", CHRIS),
             ("2023-kubecon-eu-e", CNCF_AMB), ("2023-kubecon-eu-f", ALOLITA),
             ("2023-kubecon-eu-g", KNATIVE), ("2023-kubecon-eu-h", None),
             ("2023-kubecon-eu-i", ANNI), ("2023-kubecon-eu-j", None),
             ("2023-kubecon-eu-k", KELSEY), ("2023-kubecon-eu-l", AWSTEAM),
             ("2023-kubecon-eu-m", CHERYL), ("2023-kubecon-eu-n", BARRY),
             ("2023-kubecon-eu-o", KEVIN)]),
   dict(
     venue_en="CNCF · on camera", venue_zh="CNCF · 镜头前",
     title_en="Meet the Ambassadors", title_zh="走近云原生大使",
     note_en='Filmed at KubeCon + CloudNativeCon Europe 2023 · <a href="https://youtu.be/uS698pTnw1I?si=j7xdt1GVic_jmqSG" target="_blank" rel="noopener">YouTube</a>',
     note_zh='录制于 KubeCon + CloudNativeCon Europe 2023 · <a href="https://youtu.be/uS698pTnw1I?si=j7xdt1GVic_jmqSG" target="_blank" rel="noopener">YouTube</a>',
     alt="Meet the Ambassadors, filmed at KubeCon + CloudNativeCon Europe 2023.",
     frames=[("2023-meet-the-ambassadors", None)]),
   dict(
     venue_en="CUC Meetup", venue_zh="CUC Meetup",
     title_en="Technical Leadership in Team Management", title_zh="团队管理中的技术领导力",
     note_en='Speaker · moderated by Zheng Luo · <a href="https://youtu.be/F24kUu2nFDY" target="_blank" rel="noopener">YouTube</a>',
     note_zh='主讲 · 主持：Zheng Luo · <a href="https://youtu.be/F24kUu2nFDY" target="_blank" rel="noopener">YouTube</a>',
     alt="CUC Meetup 2023, the session on technical leadership in team management.",
     frames=[("2023-cuc-meetup", None)]),
   dict(
     venue_en="StaffPlus New York", venue_zh="StaffPlus New York",
     title_en="StaffPlus New York 2023", title_zh="StaffPlus New York 2023",
     note_en="Guest · 16 March 2023 · New York · The Staff Engineer's Path, signed "
             "by its author, Tanya Reilly",
     note_zh="嘉宾 · 2023 年 3 月 16 日 · 纽约 · 作者 Tanya Reilly 在"
             "《The Staff Engineer's Path》上签名",
     alt="StaffPlus New York 2023, where Tanya Reilly signed a copy of The Staff Engineer's Path.",
     frames=[("2023-staffplus-nyc-a", None), ("2023-staffplus-nyc-b", None),
             ("2023-staffplus-nyc-c", None)]),
 ]),
 ("2022", "Detroit, online", "底特律、线上", [
   dict(
     venue_en="KubeCon + CloudNativeCon North America · Detroit",
     venue_zh="KubeCon + CloudNativeCon North America · 底特律",
     title_en="KubeCon + CloudNativeCon North America 2022",
     title_zh="KubeCon + CloudNativeCon North America 2022",
     note_en='Sole presenter · presented \u201cBuilding Multi-Tenant Routing and Scaling with Envoy\u201d · <a href="https://kccncna2022.sched.com/event/182KU/building-multi-tenant-routing-and-scaling-with-envoy-yiming-peng-amazon-web-services-inc" target="_blank" rel="noopener">session page</a> · <a href="https://www.youtube.com/watch?v=6-akjOASvxc" target="_blank" rel="noopener">YouTube</a>',
     note_zh='独立演讲《使用 Envoy 构建多租户路由与弹性伸缩》· <a href="https://kccncna2022.sched.com/event/182KU/building-multi-tenant-routing-and-scaling-with-envoy-yiming-peng-amazon-web-services-inc" target="_blank" rel="noopener">议程页面</a> · <a href="https://www.youtube.com/watch?v=6-akjOASvxc" target="_blank" rel="noopener">YouTube</a>',
     alt="KubeCon + CloudNativeCon North America 2022, the session on multi-tenant routing and scaling with Envoy.",
     frames=[("2022-kubecon-na", None)]),
   dict(
     venue_en="DockerCon", venue_zh="DockerCon",
     title_en="How developers can get to production web applications at scale, easily",
     title_zh="开发者如何轻松将 Web 应用大规模投入生产",
     note_en='With Inbal Shani and Clarinda Mascarenhas · <a href="https://www.youtube.com/watch?v=Iyp9Ugk9oRs" target="_blank" rel="noopener">YouTube</a>',
     note_zh='同场：Inbal Shani、Clarinda Mascarenhas · <a href="https://www.youtube.com/watch?v=Iyp9Ugk9oRs" target="_blank" rel="noopener">YouTube</a>',
     alt="DockerCon 2022, the AWS session on getting production web applications to scale.",
     frames=[("2022-dockercon", None)]),
   dict(
     venue_en="Containers from the Couch · livestream",
     venue_zh="Containers from the Couch · 直播",
     title_en="AWS App Runner X-Ray Integration",
     title_zh="AWS App Runner 与 X-Ray 集成",
     note_en='Guest · hosted by Adam Keller · <a href="https://youtu.be/cVr8N7enCMM" target="_blank" rel="noopener">YouTube</a>',
     note_zh='嘉宾 · 主持：Adam Keller · <a href="https://youtu.be/cVr8N7enCMM" target="_blank" rel="noopener">YouTube</a>',
     alt="Containers from the Couch, the episode on the AWS App Runner and X-Ray integration.",
     frames=[("2022-containers-from-the-couch", None)]),
 ]),
 ("2019", "Vancouver, San Diego", "温哥华、圣迭戈", [
   dict(
     venue_en="NeurIPS 2019 · Vancouver", venue_zh="NeurIPS 2019 · 温哥华",
     title_en="Neural Information Processing Systems",
     title_zh="神经信息处理系统大会",
     note_en="Guest · 8 to 14 December 2019 · Vancouver Convention Centre · my "
             "first NeurIPS, 13,000 participants, just before the pandemic · "
             '<a href="/blog/2025/neurips/">six years on</a>',
     note_zh="嘉宾 · 2019 年 12 月 8 日至 14 日 · 温哥华会议中心 · 我的第一次 "
             "NeurIPS，13,000 人参会，就在疫情之前 · "
             '<a href="/blog/2025/neurips/">六年之后</a>',
     alt="NeurIPS 2019 at the Vancouver Convention Centre.",
     frames=[("2019-neurips-yvr", None,
              "The NeurIPS 2019 badge, lanyard and programme on the first "
              "morning, the badge's QR code blanked.")]),
   dict(
     venue_en="KubeCon + CloudNativeCon North America · San Diego",
     venue_zh="KubeCon + CloudNativeCon North America · 圣迭戈",
     title_en="KubeCon + CloudNativeCon North America 2019",
     title_zh="KubeCon + CloudNativeCon North America 2019",
     note_en="The first of ten KubeCons · 18 to 21 November 2019 · San Diego "
             'Convention Center · <a href="/blog/2025/cncf10yo/">my ten KubeCons</a>',
     note_zh="十次 KubeCon 中的第一次 · 2019 年 11 月 18 日至 21 日 · 圣迭戈会议中心 · "
             '<a href="/blog/2025/cncf10yo/">我的十次 KubeCon</a>',
     alt="KubeCon + CloudNativeCon North America 2019, San Diego Convention Center.",
     frames=[("2019-kubecon-na-a", None), ("2019-kubecon-na-b", None)]),
 ]),
 ("2018", "Seattle", "西雅图", [
   dict(
     venue_en="The Collective · Seattle", venue_zh="The Collective · 西雅图",
     title_en="Kai-Fu Lee on AI Superpowers, with a book signing",
     title_zh="李开复《AI Superpowers》演讲与新书签售会",
     note_en="Guest · 27 September 2018 · presented by Town Hall Seattle at The "
             "Collective, South Lake Union",
     note_zh="嘉宾 · 2018 年 9 月 27 日 · Town Hall Seattle 主办，于 South Lake "
             "Union 的 The Collective",
     alt="Kai-Fu Lee's AI Superpowers talk and book signing at The Collective, Seattle, 27 September 2018.",
     frames=[("2018-kaifu-lee-ai-superpowers", None)]),
 ]),
]


TEAMS = [
 ("2024", "Seattle", "西雅图", [
   dict(
     venue_en="Anthropic and Amazon Bedrock",
     venue_zh="Anthropic 与 Amazon Bedrock",
     title_en="Happy hour between the two teams",
     title_zh="两个团队的欢乐时光",
     note_en="2024",
     note_zh="2024 年",
     alt="Happy hour between the Anthropic and Amazon Bedrock teams, 2024.",
     frames=[("2024-anthropic-bedrock", None)]),
 ]),
 ("2023", "Seattle", "西雅图", [
   dict(
     venue_en="Amazon", venue_zh="亚马逊",
     title_en="David Yanacek", title_zh="与 David Yanacek",
     note_en="10 May 2023",
     note_zh="2023 年 5 月 10 日",
     alt="With David Yanacek at Amazon, 10 May 2023.",
     frames=[("2023-david-yanacek", DAVID)]),
   dict(
     venue_en="Pi Day", venue_zh="圆周率日",
     title_en="Pi Day", title_zh="圆周率日",
     note_en="14 March 2023",
     note_zh="2023 年 3 月 14 日",
     alt="Pi Day 2023.",
     frames=[("2023-pi-day", None)]),
   dict(
     venue_en="Amazon", venue_zh="亚马逊",
     title_en="James Hamilton", title_zh="与 James Hamilton",
     note_en="2 February 2023",
     note_zh="2023 年 2 月 2 日",
     alt="With James Hamilton at Amazon, 2 February 2023.",
     frames=[("2023-james-hamilton", JAMES)]),
   dict(
     venue_en="Amazon", venue_zh="亚马逊",
     title_en="Junjie Tang and Desmond Zhou",
     title_zh="与 Junjie Tang、Desmond Zhou",
     note_en="2023",
     note_zh="2023 年",
     alt="With Junjie Tang and Desmond Zhou at Amazon, 2023.",
     frames=[("2023-junjie-desmond", PROSERVE)]),
 ]),
 ("2022", "Seattle", "西雅图", [
   dict(
     venue_en="Builders Day", venue_zh="Builders Day",
     title_en="Builders Day 2022", title_zh="2022 Builders Day",
     note_en="16 September 2022",
     note_zh="2022 年 9 月 16 日",
     alt="Builders Day, 16 September 2022.",
     frames=[("2022-builders-day-a", ADAM), ("2022-builders-day-b", DEEPAK)]),
   dict(
     venue_en="AWS App Runner", venue_zh="AWS App Runner",
     title_en="The App Runner team", title_zh="App Runner 团队",
     note_en="2022",
     note_zh="2022 年",
     alt="The AWS App Runner team, 2022.",
     frames=[("2022-app-runner-team", None)]),
 ]),
 ("2019", "Seattle", "西雅图", [
   dict(
     venue_en="Alexa AI · Amazon", venue_zh="Alexa AI · 亚马逊",
     title_en="Health and Wellness", title_zh="健康与养生",
     note_en="2019",
     note_zh="2019 年",
     alt="The Alexa AI Health and Wellness team, 2019.",
     frames=[("2019-alexa-health-a", None), ("2019-alexa-health-b", None),
             ("2019-alexa-health-c", TIANWEI)]),
 ]),
 ("2016", "Seattle", "西雅图", [
   dict(
     venue_en="Fintech AWS Payments · Seattle",
     venue_zh="Fintech AWS Payments · 西雅图",
     title_en="The Payments team", title_zh="Payments 团队",
     note_en="2016 to 2019, the first team",
     note_zh="2016 至 2019 年，第一支团队",
     alt="The AWS Payments team, Seattle, 2016 to 2019.",
     frames=[("2016-aws-payments", None)]),
 ]),
]


# ------------------------------------------------------------------
# Collections. One entry per page under /photos. Adding a collection is a
# table, a cover and a row here; nothing else on the site needs editing,
# because the hub rack and both counts are derived from this list.
# ------------------------------------------------------------------
COLLECTIONS = [
    dict(
        slug="events",
        occasions=lambda: EVENTS,
        title_en="Events", title_zh="活动",
        lede_en="Conference halls, panel tables, lecture rooms and broadcast "
                "desks, 2018 to 2026. Grouped by the occasion rather than by "
                "the frame.",
        lede_zh="会场、圆桌、教室与直播台，2018 至 2026。按场合归组，而不是按单张照片。",
        description="Photographs from conference halls, panel tables, lecture "
                    "rooms and broadcast desks, 2018 to 2026: NeurIPS CDMX, ICML "
                    "Vancouver, Open Source Summit North America, KubeCon Europe "
                    "and North America, DockerCon, the Packt GenAI Summit, the "
                    "Seattle Women in Tech Regatta, SMILE, B.E.L.L.E. and the "
                    "University of Washington.",
        census_extra=("Continents", "大洲", "2"),
        cover=("2023-kubecon-eu-a",
               "KubeCon + CloudNativeCon Europe 2023, cover frame of the Events "
               "collection."),
        blurb_en="Conference halls, panel tables, lecture rooms and broadcast "
                 "desks. NeurIPS in Mexico City, ICML in Vancouver, Open Source "
                 "Summit and KubeCon, DockerCon, the Packt GenAI Summit, the "
                 "Seattle Women in Tech Regatta, SMILE, B.E.L.L.E., and the "
                 "lecture rooms of the University of Washington.",
        blurb_zh="会场、圆桌、教室与直播台。墨西哥城的 NeurIPS、温哥华的 ICML、"
                 "Open Source Summit 与 KubeCon、DockerCon、Packt GenAI Summit、"
                 "西雅图 Women in Tech Regatta、SMILE、B.E.L.L.E.，以及华盛顿大学的各间教室。",
        more=[("/invited-talks.html", "The full speaking record", "完整演讲记录")],
    ),
    dict(
        slug="teams",
        occasions=lambda: TEAMS,
        title_en="Teams", title_zh="团队",
        lede_en="The people the work happened with: team photographs, and the "
                "occasional hour with someone whose name is on the architecture.",
        lede_zh="一起做事的人：团队合影，偶尔还有与某位名字写在架构里的人共处的一小时。",
        description="Team photographs from a decade at Amazon and AWS: Payments, "
                    "Alexa AI, App Runner, Bedrock, Builders Day, and hours with "
                    "Adam Selipsky, Deepak Singh and James Hamilton.",
        # A fourth cell for the tenure, which the events collection spends on
        # Continents. Two separate facts: Years measures the photographs and is
        # derived from them, so it ends where the newest frame does; At Amazon
        # is the span of the job. Neither is allowed to stand in for the other.
        census_extra=("At Amazon", "在亚马逊", "2016\u20132026"),
        cover=("2022-builders-day-a",
               "Builders Day 2022, cover frame of the Teams collection."),
        blurb_en="Colleagues and team photographs across Amazon and AWS: Alexa AI, "
                 "App Runner, Bedrock and Builders Day, plus hours with Adam "
                 "Selipsky, Deepak Singh and James Hamilton.",
        blurb_zh="亚马逊与亚马逊云科技的同事与团队合影：Alexa AI、App Runner、"
                 "Bedrock 与 Builders Day，以及与 Adam Selipsky、Deepak Singh、"
                 "James Hamilton 共处的时刻。",
        # The essay is organised by the same teams in the same order, chapter by
        # chapter, so it comes first: this page is its photographic index.
        more=[("/blog/2026/curiosity-driven-builder/", "Builder's Journey",
               "构建者之旅"),
              ("/blog/2026/decade/", "Decade at Amazon", "亚马逊十年")],
    ),
]


I = " " * 3

BEGIN = "         <!-- SHEET:BEGIN generated by scripts/generate_photo_pages.py -->"
END = "         <!-- SHEET:END -->"
RACK_BEGIN = "         <!-- RACK:BEGIN generated by scripts/generate_photo_pages.py -->"
RACK_END = "         <!-- RACK:END -->"


def measured(slug: str) -> dict[str, list[tuple[int, int]]]:
    """frame slug -> [(width, height), ...] widest first, read off the files."""
    out: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for f in sorted((ROOT / "assets" / "photos" / slug).glob("*.webp")):
        stem, _, _w = f.stem.rpartition("-")
        with Image.open(f) as im:
            out[stem].append((im.width, im.height))
    for k in out:
        out[k].sort(key=lambda wh: -wh[0])
    return out


def bi(en: str, zh: str, cls: str | None = None, tag: str = "span") -> str:
    """A bilingual pair, collapsed to one element when both halves match."""
    attr = f' class="{cls}"' if cls else ""
    if en == zh:
        return f"<{tag}{attr}>{en}</{tag}>"
    return (f'<{tag}{attr}><span class="lang-en">{en}</span>'
            f'<span class="lang-zh" hidden>{zh}</span></{tag}>')


def frame_html(coll, slug, credit, alt, count, ind, F) -> str:
    variants = F.get(slug)
    if not variants:
        sys.exit(f"no built derivatives for {slug!r} in collection {coll!r}. "
                 "Run scripts/build_photo_derivatives.py first.")
    base = f"/assets/photos/{coll}/{slug}"
    w, h = variants[0]
    full = f"{base}-{w}.webp"
    pad = " " * (len(ind) + 9)

    img = [f'{ind}   <img src="{full}"']
    if len(variants) > 1:
        srcset = (",\n" + pad).join(f"{base}-{vw}.webp {vw}w" for vw, _ in variants)
        img.append(f'{pad}srcset="{srcset}"')
    img.append(f'{pad}sizes="{SIZES[min(count, 3)]}"')
    img.append(f'{pad}data-full="{full}"')
    img.append(f'{pad}width="{w}" height="{h}" loading="lazy" decoding="async"')
    img.append(f'{pad}alt="{alt}">')

    out = [f'{ind}<figure class="figure frame">', "\n".join(img)]
    if credit:
        # A third element names the class: f-credit for a person, f-caption for
        # a note about what the frame shows. Defaults to a credit.
        cls = credit[2] if len(credit) > 2 else "f-credit"
        out.append(f'{ind}   {bi(credit[0], credit[1], cls, "figcaption")}')
    out.append(f"{ind}</figure>")
    return "\n".join(out)


def occasion_html(coll, o, ind, F) -> str:
    n = len(o["frames"])
    out = [f'{ind}<article class="occasion">',
           f'{ind}   <header class="occ-head">',
           f'{ind}      {bi(o["venue_en"], o["venue_zh"], "f-venue", "p")}',
           f'{ind}      {bi(o["title_en"], o["title_zh"], "f-title", "h3")}',
           f'{ind}      {bi(o["note_en"], o["note_zh"], "f-note", "p")}',
           f'{ind}   </header>',
           f'{ind}   <div class="sheet" data-frames="{n}">']
    for frame in o["frames"]:
        # (slug, credit) normally; a third element overrides the occasion alt,
        # for the frames whose content is documented somewhere reliable.
        slug, credit = frame[0], frame[1]
        alt = frame[2] if len(frame) > 2 else o["alt"]
        out.append(frame_html(coll, slug, credit, alt, n, ind + "      ", F))
    out += [f"{ind}   </div>", f"{ind}</article>"]
    return "\n".join(out)


def build_body(coll: str, occasions, F) -> str:
    blocks = []
    for year, place_en, place_zh, occs in occasions:
        n = sum(len(o["frames"]) for o in occs)
        w_en, w_zh = count_words(n)
        ind = I * 3
        b = [f'{ind}<!-- {"=" * 60}',
             f'{ind}     {year}',
             f'{ind}     {"=" * 60} -->',
             f'{ind}<section class="rise" id="y{year}">',
             f'{ind}   <div class="year">',
             f'{ind}      <h2>{year}</h2>',
             f'{ind}      {bi(f"{w_en} · {place_en}", f"{w_zh} · {place_zh}", None, "p")}',
             f'{ind}   </div>', ""]
        for o in occs:
            b.append(occasion_html(coll, o, ind + I, F))
            b.append("")
        b.append(f"{ind}</section>")
        blocks.append("\n".join(b))
    return "\n\n".join(blocks)


LEAD_COMMENT = """         <!-- Years run newest first, matching every other dated listing on the
              site, and within a year the occasions do too wherever a date is
              known. A date is printed only where there is evidence for it:
              EXIF DateTimeOriginal, a filename that carries the day, or a
              published schedule.

              Each occasion carries its own header, so the frames under it need
              no repeated caption; a credit line appears only where a frame has
              one, and a credit names a person rather than remarking on the
              page. Alt text describes the occasion unless a frame's content is
              documented somewhere reliable, in which case that wording is
              reused rather than reinvented. -->"""

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
   <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>{title_en} · Photographs · Peng, Andy</title>
      <meta name="author" content="Peng, Andy">
      <meta name="description" content="{description}">
      <link rel="canonical" href="https://pengandy.com/photos/{slug}/">
      <!-- Listed: no robots meta, so generate_sitemap.py puts the page in the
           tree at /sitemap. These pages were unlisted when the collection
           opened, which is why the sitemap did not carry them; that was the
           meta doing its job, not the generator missing a subdirectory.
           Still absent from the footer directory, like /office: reachable from
           the sitemap is reach enough for a shelf of photographs. The card a
           social platform shows falls back to the site icon until these pages
           get one of their own. -->

      <link rel="icon" href="/assets/brand/logo-mark.svg" type="image/svg+xml">
      <link rel="icon" href="/assets/brand/icon-512.png" sizes="512x512" type="image/png">
      <link rel="apple-touch-icon" href="/assets/brand/apple-touch-icon.png" sizes="180x180">
      <link rel="manifest" href="/site.webmanifest">

      <link rel="preconnect" href="https://fonts.googleapis.com">
      <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
      <link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600&display=swap" rel="stylesheet">

      <link rel="stylesheet" href="/assets/css/shell.css">
      <link rel="stylesheet" href="/assets/css/photos.css">
      <script src="/assets/js/shell.js" defer></script>
      <script src="/assets/js/photos.js" defer></script>

      <script async src="https://www.googletagmanager.com/gtag/js?id=G-HTV795ZMCP"></script>
      <script>
         window.dataLayer = window.dataLayer || [];
         function gtag(){{dataLayer.push(arguments);}}
         gtag('js', new Date());
         gtag('config', 'G-HTV795ZMCP');
      </script>
   </head>

   <body data-nav-match="photos">
      <a class="skip" href="#main">Skip to content</a>
      <nav class="nav" aria-label="Primary" data-shell-nav></nav>

      <header class="shell page-head">
         <p class="eyebrow">
            <span class="lang-en"><a href="/photos/">Photographs</a></span>
            <span class="lang-zh" hidden><a href="/photos/">摄影</a></span>
         </p>
         <h1 class="page-title">
            <span class="lang-en">{title_en}</span>
            <span class="lang-zh" hidden>{title_zh}</span>
         </h1>
         <p class="page-lede">
            <span class="lang-en">{lede_en}</span>
            <span class="lang-zh" hidden>{lede_zh}</span>
         </p>
      </header>

      <main class="shell" id="main" style="padding-bottom:var(--movement)">

         <section class="rise">
            <dl class="census">
{census}
            </dl>
         </section>

{lead}

{begin}

{body}

{end}

         <p class="more">
{more}
         </p>

      </main>

      <!-- Viewer. One instance, filled from whichever frame was clicked. -->
      <div class="lb" id="lb" hidden role="dialog" aria-modal="true" aria-label="Photograph viewer">
         <button class="lb-x" type="button" data-lb-close aria-label="Close viewer">&times;</button>
         <button class="lb-prev" type="button" data-lb-step="-1" aria-label="Previous photograph">&lsaquo;</button>
         <button class="lb-next" type="button" data-lb-step="1" aria-label="Next photograph">&rsaquo;</button>
         <figure class="lb-stage">
            <img id="lb-img" alt="">
            <figcaption id="lb-cap"></figcaption>
         </figure>
      </div>

      <footer class="foot" data-shell-footer></footer>
   </body>
</html>
"""


def census_html(frames: int, span: str, occasions: int, extra) -> str:
    rows = [("Frames", "照片", str(frames)),
            ("Years", "年份", span),
            ("Occasions", "场合", str(occasions))]
    if extra:
        rows.append(extra)
    out = []
    for en, zh, val in rows:
        out += ["               <div>",
                f'                  <dt>{bi(en, zh)}</dt>',
                f"                  <dd>{val}</dd>",
                "               </div>"]
    return "\n".join(out)


def more_html(links) -> str:
    out = []
    for i, (href, en, zh) in enumerate(links + [("/photos/", "All photograph collections",
                                                 "全部摄影合集")]):
        style = ' style="margin-left:clamp(18px,2vw,32px)"' if i else ""
        out += [f'            <a class="link" href="{href}"{style}>',
                f"               {bi(en, zh)} →", "            </a>"]
    return "\n".join(out)


def totals(occasions):
    frames = sum(len(o["frames"]) for _, _, _, occs in occasions for o in occs)
    n_occ = sum(len(occs) for _, _, _, occs in occasions)
    years = [y for y, *_ in occasions]
    return frames, n_occ, f"{min(years)}\u2013{max(years)}"


def rack_html(stats) -> str:
    """The hub's collection rows, one per collection, newest content first."""
    out = []
    for c, (frames, n_occ, span, cw, ch) in stats:
        cover_slug, cover_alt = c["cover"]
        out += [
            "            <li>",
            '               <figure class="rack-cover">',
            f'                  <img src="/assets/photos/{c["slug"]}/{cover_slug}-{cw}.webp"',
            f'                       width="{cw}" height="{ch}" loading="lazy" decoding="async"',
            f'                       alt="{cover_alt}">',
            "               </figure>",
            "               <div>",
            '                  <p class="count">',
            f'                     <span class="lang-en">{frames} frames · {n_occ} occasions · {span}</span>',
            f'                     <span class="lang-zh" hidden>{frames} 张 · {n_occ} 个场合 · {span}</span>',
            "                  </p>",
            "                  <h2>",
            f'                     <a href="/photos/{c["slug"]}/">',
            f'                        <span class="lang-en">{c["title_en"]}</span>',
            f'                        <span class="lang-zh" hidden>{c["title_zh"]}</span>',
            "                     </a>",
            "                  </h2>",
            '                  <p class="blurb">',
            f'                     <span class="lang-en">{c["blurb_en"]}</span>',
            f'                     <span class="lang-zh" hidden>{c["blurb_zh"]}</span>',
            "                  </p>",
            '                  <span class="go">',
            '                     <span class="lang-en">Open the collection</span>'
            '<span class="lang-zh" hidden>进入合集</span> →',
            "                  </span>",
            "               </div>",
            "            </li>",
        ]
    return "\n".join(out)


def render() -> dict[pathlib.Path, str]:
    """Path -> new text, for every page this script owns."""
    pages: dict[pathlib.Path, str] = {}
    stats = []

    for c in COLLECTIONS:
        slug = c["slug"]
        occasions = c["occasions"]()
        F = measured(slug)
        used = {f[0] for _, _, _, occs in occasions for o in occs for f in o["frames"]}
        orphans = sorted(set(F) - used)
        if orphans:
            print(f"warning: built but unused in {slug}: {', '.join(orphans)}",
                  file=sys.stderr)

        frames, n_occ, span = totals(occasions)
        cover_slug, _ = c["cover"]
        if cover_slug not in F:
            sys.exit(f"cover {cover_slug!r} has no built derivatives")
        cw, ch = min(F[cover_slug], key=lambda wh: wh[0])
        stats.append((c, (frames, n_occ, span, cw, ch)))

        pages[ROOT / "photos" / slug / "index.html"] = PAGE_TEMPLATE.format(
            slug=slug, title_en=c["title_en"], title_zh=c["title_zh"],
            description=c["description"],
            lede_en=c["lede_en"], lede_zh=c["lede_zh"],
            census=census_html(frames, span, n_occ, c["census_extra"]),
            lead=LEAD_COMMENT, begin=BEGIN, end=END,
            body=build_body(slug, occasions, F),
            more=more_html(c["more"]),
        )

    hub = HUB.read_text(encoding="utf-8")
    head, sep, rest = hub.partition(RACK_BEGIN)
    if not sep:
        sys.exit(f"marker missing from {HUB}: {RACK_BEGIN.strip()}")
    _old, sep2, tail = rest.partition(RACK_END)
    if not sep2:
        sys.exit(f"marker missing from {HUB}: {RACK_END.strip()}")
    hub = head + RACK_BEGIN + "\n" + rack_html(stats) + "\n" + RACK_END + tail
    pages[HUB] = hub
    return pages


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if the pages are not what this would write")
    args = ap.parse_args()

    pages = render()
    stale = [p.relative_to(ROOT) for p, new in pages.items()
             if not p.exists() or p.read_text(encoding="utf-8") != new]

    if args.check:
        if stale:
            print("stale: " + ", ".join(map(str, stale)), file=sys.stderr)
            return 1
        print("photo pages are current.")
        return 0

    for p, new in pages.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(new, encoding="utf-8")
    for c in COLLECTIONS:
        frames, n_occ, span = totals(c["occasions"]())
        print(f"wrote photos/{c['slug']}/index.html: {frames} frames across "
              f"{n_occ} occasions, {span}")
    print(f"wrote {HUB.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
