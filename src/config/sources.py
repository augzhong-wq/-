"""
信息源完整配置 —— AI动态监测渠道清单

包含用户指定的全部65个信息源、190+个URL，不折不扣。
"""

from dataclasses import dataclass, field


@dataclass
class Source:
    """信息源定义"""
    name: str                       # 源名称
    category: str                   # 大类
    sub_category: str               # 子类
    urls: list[str] = field(default_factory=list)  # 采集URL列表
    collector_type: str = "http"    # "http" 或 "browser"
    priority: int = 3               # 源优先级 1-5（5最高）
    notes: str = ""                 # 备注


# ═══════════════════════════════════════════════════════════════
# 完整信息源清单 — 严格按照用户提供的渠道清单
# ═══════════════════════════════════════════════════════════════

SOURCES: list[Source] = [

    # ─────────────────────────────────────────────────────
    # 一、AI巨头与顶级实验室
    # ─────────────────────────────────────────────────────

    # 1. Apple
    Source(
        name="Apple",
        category="AI巨头与顶级实验室",
        sub_category="AI龙头企业",
        urls=[
            "https://machinelearning.apple.com/highlights",
            "https://machinelearning.apple.com/research",
        ],
        collector_type="http",
        priority=5,
    ),

    # 2. Microsoft
    Source(
        name="Microsoft",
        category="AI巨头与顶级实验室",
        sub_category="AI龙头企业",
        urls=[
            "https://www.microsoft.com/en-us/research/publications/",
            "https://www.microsoft.com/en-us/research/blog/",
            "https://www.microsoft.com/en-us/research/research-area/artificial-intelligence/",
            "https://azure.microsoft.com/en-us/blog/category/ai-machine-learning/",
        ],
        collector_type="http",
        priority=5,
    ),

    # 3. Alphabet/Google (DeepMind + Google Research)
    Source(
        name="Alphabet/Google",
        category="AI巨头与顶级实验室",
        sub_category="AI龙头企业",
        urls=[
            "https://deepmind.google/research/publications/",
            "https://deepmind.google/research/projects/",
            "https://deepmind.google/blog/",
            "https://research.google/resources/our-projects/",
            "https://research.google/pubs/",
        ],
        collector_type="http",
        priority=5,
    ),

    # 4. Amazon/AWS
    Source(
        name="Amazon/AWS",
        category="AI巨头与顶级实验室",
        sub_category="AI龙头企业",
        urls=[
            "https://aws.amazon.com/cn/blogs/aws-insights/",
            "https://aws.amazon.com/cn/blogs/aws/",
            "https://aws.amazon.com/cn/blogs/big-data/",
            "https://www.amazon.science/publications",
            "https://www.amazon.science/research-areas/machine-learning",
            "https://www.amazon.science/blog",
            "https://www.amazon.science/news",
        ],
        collector_type="http",
        priority=5,
    ),

    # 5. Meta
    Source(
        name="Meta",
        category="AI巨头与顶级实验室",
        sub_category="AI龙头企业",
        urls=[
            "https://ai.meta.com/results/?content_types%5B0%5D=publication",
            "https://ai.meta.com/research/#projects",
            "https://research.facebook.com/blog/",
        ],
        collector_type="http",
        priority=5,
    ),

    # 6. NVIDIA
    Source(
        name="NVIDIA",
        category="AI巨头与顶级实验室",
        sub_category="AI龙头企业",
        urls=[
            "https://developer.nvidia.com/blog",
            "https://blogs.nvidia.com/",
            "https://nvidianews.nvidia.com/news",
        ],
        collector_type="http",
        priority=5,
        notes="英伟达_Fabless_EN_博客新闻",
    ),

    # 7. OpenAI
    Source(
        name="OpenAI",
        category="AI巨头与顶级实验室",
        sub_category="AI龙头企业",
        urls=[
            "https://openai.com/zh-Hans-CN/research/index/",
            "https://openai.com/zh-Hans-CN/research/index/publication/",
            "https://openai.com/zh-Hans-CN/news/",
            "https://openai.com/research/index/conclusion/",
            "https://openai.com/research/index/release/",
            "https://openai.com/research/index/milestone/",
        ],
        collector_type="browser",
        priority=5,
    ),

    # 8. Anthropic
    Source(
        name="Anthropic",
        category="AI巨头与顶级实验室",
        sub_category="AI龙头企业",
        urls=[
            "https://www.anthropic.com/blog",
            "https://claude.com/blog",
        ],
        collector_type="http",
        priority=5,
    ),

    # 9. xAI (马斯克)
    Source(
        name="xAI",
        category="AI巨头与顶级实验室",
        sub_category="新兴AI独角兽",
        urls=[
            "https://x.ai/news",
        ],
        collector_type="http",
        priority=4,
    ),

    # 10. Mistral AI
    Source(
        name="Mistral AI",
        category="AI巨头与顶级实验室",
        sub_category="新兴AI独角兽",
        urls=[
            "https://mistral.ai/news?category=research",
        ],
        collector_type="http",
        priority=4,
    ),

    # 11. AMD
    Source(
        name="AMD",
        category="AI巨头与顶级实验室",
        sub_category="AI芯片公司",
        urls=[
            "https://www.amd.com/en/corporate/newsroom/press-releases",
        ],
        collector_type="browser",
        priority=4,
        notes="AMD_Fabless_EN_新闻（爬虫失效，使用浏览器采集）",
    ),

    # 12. Intel
    Source(
        name="Intel",
        category="AI巨头与顶级实验室",
        sub_category="AI芯片公司",
        urls=[
            "https://newsroom.intel.com/all-news",
        ],
        collector_type="browser",
        priority=4,
        notes="Intel_IDM&Foundry_EN_新闻（爬虫失效，使用浏览器采集）",
    ),

    # 13. Qualcomm
    Source(
        name="Qualcomm",
        category="AI巨头与顶级实验室",
        sub_category="AI芯片公司",
        urls=[
            "https://www.qualcomm.com/news",
            "https://www.qualcomm.com/news/onq/",
        ],
        collector_type="browser",
        priority=4,
        notes="高通Qualcomm_Fabless_EN_新闻（爬虫失效，使用浏览器采集）",
    ),

    # ─────────────────────────────────────────────────────
    # 二、高校与研究机构
    # ─────────────────────────────────────────────────────

    # 14. Stanford HAI
    Source(
        name="Stanford HAI",
        category="高校与研究机构",
        sub_category="高校",
        urls=[
            "https://hai.stanford.edu/news/blog",
            "https://hai.stanford.edu/policy/policy-publications",
        ],
        collector_type="browser",
        priority=5,
        notes="斯坦福大学人工智能研究院（反爬，使用浏览器采集）",
    ),

    # 15. Berkeley BAIR
    Source(
        name="Berkeley BAIR",
        category="高校与研究机构",
        sub_category="高校",
        urls=[
            "https://eecs.berkeley.edu/news",
        ],
        collector_type="http",
        priority=4,
        notes="Berkeley EECS_EN_新闻",
    ),

    # 16. Alan Turing Institute
    Source(
        name="Alan Turing Institute",
        category="高校与研究机构",
        sub_category="欧洲研究机构",
        urls=[
            "https://www.turing.ac.uk/science-innovation",
            "https://www.turing.ac.uk/blog",
            "https://www.turing.ac.uk/news/publications",
        ],
        collector_type="http",
        priority=4,
    ),

    # 17. MILA (蒙特利尔)
    Source(
        name="MILA",
        category="高校与研究机构",
        sub_category="加拿大AI生态",
        urls=[
            "https://mila.quebec/en/research/blog",
            "https://mila.quebec/en/research/publications",
            "https://mila.quebec/en/insights",
        ],
        collector_type="http",
        priority=4,
    ),

    # 18. Vector Institute (多伦多)
    Source(
        name="Vector Institute",
        category="高校与研究机构",
        sub_category="加拿大AI生态",
        urls=[
            "https://vectorinstitute.ai/research/",
            "https://vectorinstitute.ai/research/publications/",
            "https://vectorinstitute.ai/insights/ai-research-insights/",
            "https://vectorinstitute.ai/insights/newsroom/",
        ],
        collector_type="http",
        priority=3,
    ),

    # 19. Amii (阿尔伯塔)
    Source(
        name="Amii",
        category="高校与研究机构",
        sub_category="加拿大AI生态",
        urls=[
            "https://www.amii.ca/research",
            "https://www.amii.ca/updates-insights",
            "https://www.amii.ca/press-and-media",
        ],
        collector_type="http",
        priority=3,
    ),

    # 20. Fei-Fei Li (via Stanford HAI - same URLs)
    Source(
        name="Fei-Fei Li",
        category="高校与研究机构",
        sub_category="学者言论",
        urls=[
            "https://hai.stanford.edu/news/blog",
            "https://hai.stanford.edu/policy/policy-publications",
        ],
        collector_type="browser",
        priority=4,
        notes="斯坦福大学人工智能研究院_国外智库_EN_博客白皮书政策",
    ),

    # 21. Nature Machine Intelligence
    Source(
        name="Nature Machine Intelligence",
        category="高校与研究机构",
        sub_category="学术期刊",
        urls=[
            "https://www.nature.com/natmachintell/news-and-comment",
            "https://www.nature.com/natmachintell/research-articles",
            "https://www.nature.com/natmachintell/reviews-and-analysis",
            "https://www.nature.com/natmachintell/collections",
        ],
        collector_type="http",
        priority=4,
    ),

    # 22. JMLR
    Source(
        name="JMLR",
        category="高校与研究机构",
        sub_category="学术期刊",
        urls=[
            "https://jmlr.org/news.html",
        ],
        collector_type="http",
        priority=3,
    ),

    # ─────────────────────────────────────────────────────
    # 三、学术会议
    # ─────────────────────────────────────────────────────

    # 23. NeurIPS
    Source(
        name="NeurIPS",
        category="学术会议",
        sub_category="官网/社媒",
        urls=[
            "https://neurips.cc/Conferences/2025/Press",
            "https://blog.neurips.cc/",
        ],
        collector_type="http",
        priority=3,
    ),

    # 24. ICML
    Source(
        name="ICML",
        category="学术会议",
        sub_category="官网/社媒",
        urls=[
            "https://icml.cc/Conferences/2025/Press",
        ],
        collector_type="http",
        priority=3,
    ),

    # 25. ICLR
    Source(
        name="ICLR",
        category="学术会议",
        sub_category="官网/社媒",
        urls=[
            "https://blog.iclr.cc/",
            "https://iclr.cc/Conferences/2025/Press",
        ],
        collector_type="http",
        priority=3,
    ),

    # ─────────────────────────────────────────────────────
    # 四、专业媒体与通讯
    # ─────────────────────────────────────────────────────

    # 26. Reuters Tech
    Source(
        name="Reuters Tech",
        category="专业媒体与通讯",
        sub_category="科技与商业媒体",
        urls=[
            "https://www.reuters.com/technology/",
            "https://www.reuters.com/world/",
            "https://www.reuters.com/legal/",
            "https://www.reuters.com/markets/",
            "https://www.reuters.com/commentary/breakingviews/",
            "https://www.reuters.com/business/",
        ],
        collector_type="browser",
        priority=5,
        notes="路透社_EN_技术及国际新闻",
    ),

    # 27. The Verge
    Source(
        name="The Verge",
        category="专业媒体与通讯",
        sub_category="科技与商业媒体",
        urls=[
            "http://www.theverge.com/tech",
            "https://www.theverge.com/health",
            "https://www.theverge.com/autonomous-cars",
        ],
        collector_type="http",
        priority=4,
        notes="the Verge_EN_科技新闻",
    ),

    # 28. TechCrunch
    Source(
        name="TechCrunch",
        category="专业媒体与通讯",
        sub_category="科技与商业媒体",
        urls=[
            "https://techcrunch.com/startups/",
            "https://techcrunch.com/gadgets/",
            "https://techcrunch.com/apps/",
            "https://techcrunch.com/",
        ],
        collector_type="http",
        priority=4,
        notes="techcrunch_EN_startups&gadgets新闻",
    ),

    # 29. MIT Technology Review
    Source(
        name="MIT Technology Review",
        category="专业媒体与通讯",
        sub_category="科技与商业媒体",
        urls=[
            "https://www.technologyreview.com/",
        ],
        collector_type="http",
        priority=5,
        notes="MIT Technology Review_EN_新闻",
    ),

    # 30. IEEE Spectrum
    Source(
        name="IEEE Spectrum",
        category="专业媒体与通讯",
        sub_category="科技与商业媒体",
        urls=[
            "https://spectrum.ieee.org/topic/artificial-intelligence/",
            "https://spectrum.ieee.org/topic/computing/",
            "https://spectrum.ieee.org/topic/robotics/",
            "https://spectrum.ieee.org/topic/semiconductors/",
            "https://spectrum.ieee.org/topic/telecommunications/",
            "https://spectrum.ieee.org/topic/transportation/",
        ],
        collector_type="http",
        priority=4,
        notes="IEEE AI_EN_AI新闻",
    ),

    # 31. SemiAnalysis
    Source(
        name="SemiAnalysis",
        category="专业媒体与通讯",
        sub_category="战略分析平台",
        urls=[
            "https://semianalysis.com/",
        ],
        collector_type="http",
        priority=4,
    ),

    # 32. NVIDIA AI Podcast (same URLs as NVIDIA main)
    Source(
        name="NVIDIA AI Podcast",
        category="专业媒体与通讯",
        sub_category="播客",
        urls=[
            "https://developer.nvidia.com/blog",
            "https://blogs.nvidia.com/",
            "https://nvidianews.nvidia.com/news",
        ],
        collector_type="http",
        priority=3,
        notes="英伟达_Fabless_EN_博客新闻",
    ),

    # 33. 机器之心
    Source(
        name="机器之心",
        category="专业媒体与通讯",
        sub_category="中文快速聚合",
        urls=[
            "https://www.jiqizhixin.com/",
        ],
        collector_type="http",
        priority=5,
    ),

    # 34. 量子位
    Source(
        name="量子位",
        category="专业媒体与通讯",
        sub_category="中文快速聚合",
        urls=[
            "https://www.qbitai.com/category/zhiku",
            "https://www.qbitai.com/category/auto",
            "https://www.qbitai.com/category/%e8%b5%84%e8%ae%af",
        ],
        collector_type="http",
        priority=5,
    ),

    # 35. 布鲁金斯学会
    Source(
        name="布鲁金斯学会",
        category="专业媒体与通讯",
        sub_category="智库与咨询机构",
        urls=[
            "https://www.brookings.edu/research-commentary/",
            "https://www.brookings.edu/topics/technology-innovation/",
            "https://www.brookings.edu/topics/international-affairs/",
            "https://www.brookings.edu/topics/u-s-economy/",
            "https://www.brookings.edu/topics/global-inequality/",
            "https://www.brookings.edu/topics/u-s-politics-government/",
            "https://www.brookings.edu/blog/techtank/",
            "https://www.brookings.edu/blog/order-from-chaos/",
            "https://www.brookings.edu/blog/future-development/",
            "https://www.brookings.edu/techstream/",
            "https://www.brookings.edu/regions/eurasia/russia/",
            "https://www.brookings.edu/topics/climate-change/",
            "https://www.brookings.edu/topics/race-in-american-public-policy/",
            "https://www.brookings.edu/topics/climate-energy/",
            "https://www.brookings.edu/topics/national-security/",
            "https://www.brookings.edu/topics/health-care-2/",
            "https://www.brookings.edu/regions/asia-the-pacific/",
            "https://www.brookings.edu/regions/europe/",
            "https://www.brookings.edu/regions/africa/",
            "https://www.brookings.edu/regions/eurasia/",
            "https://www.brookings.edu/regions/north-america/",
            "https://www.brookings.edu/regions/latin-america-the-caribbean/",
            "https://www.brookings.edu/regions/middle-east-north-africa/",
            "https://www.brookings.edu/topics/artificial-intelligence/",
        ],
        collector_type="http",
        priority=4,
        notes="布鲁金斯学会_国外智库_EN_研究及博客",
    ),

    # 36. 卡内基国际和平基金会
    Source(
        name="卡内基国际和平基金会",
        category="专业媒体与通讯",
        sub_category="智库与咨询机构",
        urls=[
            "https://carnegieendowment.org/",
        ],
        collector_type="http",
        priority=4,
        notes="卡内基国际和平研究院_国外智库_EN_译报资源",
    ),

    # 37. 麦肯锡
    Source(
        name="麦肯锡",
        category="专业媒体与通讯",
        sub_category="智库与咨询机构",
        urls=[
            "https://www.mckinsey.com/featured-insights",
            "https://www.mckinsey.com/mgi/our-research/all-research",
            "https://www.mckinsey.com/industries/advanced-electronics/our-insights",
            "https://www.mckinsey.com/industries/aerospace-and-defense/our-insights",
            "https://www.mckinsey.com/industries/metals-and-mining/our-insights",
            "https://www.mckinsey.com/industries/technology-media-and-telecommunications/our-insights",
            "https://www.mckinsey.com/industries/semiconductors/our-insights",
            "https://www.mckinsey.com/industries/public-sector/our-insights",
            "https://www.mckinsey.com/industries/oil-and-gas/our-insights",
            "https://www.mckinsey.com/industries/financial-services/our-insights",
            "https://www.mckinsey.com/industries/automotive-and-assembly/our-insights",
        ],
        collector_type="http",
        priority=4,
        notes="麦肯锡公司_国外智库_EN_洞见",
    ),

    # 38. 波士顿咨询 BCG
    Source(
        name="波士顿咨询BCG",
        category="专业媒体与通讯",
        sub_category="智库与咨询机构",
        urls=[
            "https://www.bcg.com/capabilities/digital-technology-data/insights",
            "https://www.bcg.com/industries/automotive/insights",
            "https://www.bcg.com/industries/telecommunications/insights",
            "https://www.bcg.com/capabilities/innovation-strategy-delivery/insights",
            "https://www.bcg.com/publications",
            "https://www.bcg.com/search?q=&s=1&f7=00000171-f17b-d394-ab73-f3fbae0d0000",
        ],
        collector_type="http",
        priority=4,
        notes="波士顿咨询BCG_国外智库_EN_洞察",
    ),

    # 39. 德勤
    Source(
        name="德勤",
        category="专业媒体与通讯",
        sub_category="智库与咨询机构",
        urls=[
            "https://www2.deloitte.com/us/en/insights/economy/us-economic-forecast.html",
            "https://www2.deloitte.com/us/en/industries/government-public-services.html?icid=top_government-public-services",
            "https://www2.deloitte.com/us/en/industries/energy-resources-industrials.html?icid=top_energy-resources-industrials",
            "https://www2.deloitte.com/us/en/insights/industry/technology.html",
            "https://www2.deloitte.com/us/en/insights/industry/telecommunications.html",
            "https://www2.deloitte.com/us/en/footerlinks/pressreleasespage.html?icid=bottom_pressreleasespage&q=*&sp_x_18=content-type&sp_s=date-published-d%7Ctitle&sp_q_18=%22Press%20releases%22",
            "https://www.bcg.com/capabilities/innovation-strategy-delivery/insights",
        ],
        collector_type="http",
        priority=4,
        notes="德勤咨询公司_国外智库_EN_英文研究报告",
    ),

    # 40. CB Insights
    Source(
        name="CB Insights",
        category="专业媒体与通讯",
        sub_category="智库与咨询机构",
        urls=[
            "https://www.cbinsights.com/research/",
            "https://www.cbinsights.com/research/report",
        ],
        collector_type="http",
        priority=4,
        notes="CB Insights_国外智库_EN_研究",
    ),

    # 41. McKinsey State of AI (same as 麦肯锡)
    Source(
        name="McKinsey State of AI",
        category="专业媒体与通讯",
        sub_category="年度战略报告",
        urls=[
            "https://www.mckinsey.com/featured-insights",
            "https://www.mckinsey.com/mgi/our-research/all-research",
            "https://www.mckinsey.com/industries/advanced-electronics/our-insights",
            "https://www.mckinsey.com/industries/aerospace-and-defense/our-insights",
            "https://www.mckinsey.com/industries/metals-and-mining/our-insights",
            "https://www.mckinsey.com/industries/technology-media-and-telecommunications/our-insights",
            "https://www.mckinsey.com/industries/semiconductors/our-insights",
            "https://www.mckinsey.com/industries/public-sector/our-insights",
            "https://www.mckinsey.com/industries/oil-and-gas/our-insights",
            "https://www.mckinsey.com/industries/financial-services/our-insights",
            "https://www.mckinsey.com/industries/automotive-and-assembly/our-insights",
        ],
        collector_type="http",
        priority=4,
        notes="麦肯锡公司_国外智库_EN_洞见",
    ),

    # 42. Goldman Sachs AI研究
    Source(
        name="Goldman Sachs AI研究",
        category="专业媒体与通讯",
        sub_category="年度战略报告",
        urls=[
            "https://www.goldmansachs.com/insights",
            "https://www.goldmansachs.com/insights/articles",
            "https://www.goldmansachs.com/insights/reports",
        ],
        collector_type="http",
        priority=4,
    ),

    # ─────────────────────────────────────────────────────
    # 五、安全评测
    # ─────────────────────────────────────────────────────

    # 43. 美国 AI 安全研究所 (NIST)
    Source(
        name="美国AI安全研究所",
        category="安全评测",
        sub_category="安全评测",
        urls=[
            "https://www.nist.gov/news-events/news/search",
            "https://www.nist.gov/news-events/news-updates/search",
            "https://www.nist.gov/publications",
        ],
        collector_type="http",
        priority=4,
        notes="美国国家标准与技术研究院NIST_国外智库_EN_新闻报告",
    ),

    # ─────────────────────────────────────────────────────
    # 六、投融资与生态
    # ─────────────────────────────────────────────────────

    # 44. CB Insights Newsletter
    Source(
        name="CB Insights Newsletter",
        category="投融资与生态",
        sub_category="投融资分析",
        urls=[
            "https://www.cbinsights.com/research/",
            "https://www.cbinsights.com/research/report",
        ],
        collector_type="http",
        priority=4,
        notes="CB Insights_国外智库_EN_研究",
    ),

    # 45. Business Wire
    Source(
        name="Business Wire",
        category="投融资与生态",
        sub_category="PR新闻通讯社",
        urls=[
            "https://www.businesswire.com/portal/site/home/news/industry/?vnsId=31335",
            "https://www.businesswire.com/portal/site/home/news/industry/?vnsId=31337",
            "https://www.businesswire.com/portal/site/home/news/industry/?vnsId=31121",
            "https://www.businesswire.com/portal/site/home/news/industry/?vnsId=31209",
            "https://www.businesswire.com/portal/site/home/news/industry/?vnsId=31250",
            "https://www.businesswire.com/portal/site/home/news/industry/?vnsId=30901",
            "https://www.businesswire.com/portal/site/home/news/industry/?vnsId=31251",
            "https://www.businesswire.com/portal/site/home/news/industry/?vnsId=31234",
            "https://www.businesswire.com/portal/site/home/news/industry/?vnsId=31249",
            "https://www.businesswire.com/portal/site/home/news/industry/?vnsId=31264",
        ],
        collector_type="http",
        priority=3,
        notes="美国商业资讯_EN_新闻",
    ),

    # 46. PR Newswire
    Source(
        name="PR Newswire",
        category="投融资与生态",
        sub_category="PR新闻通讯社",
        urls=[
            "http://www.prnewswire.com/news-releases/business-technology-latest-news/electronic-design-automation-list/",
            "https://www.prnewswire.com/news-releases/heavy-industry-manufacturing-latest-news/",
            "https://www.prnewswire.com/news-releases/telecommunications-latest-news/",
            "https://www.prnewswire.com/news-releases/consumer-technology-latest-news/",
            "https://www.prnewswire.com/news-releases/consumer-technology-latest-news/consumer-technology-latest-news-list/",
            "https://www.prnewswire.com/news-releases/heavy-industry-manufacturing-latest-news/heavy-industry-manufacturing-latest-news-list/",
            "https://www.prnewswire.com/news-releases/telecommunications-latest-news/telecommunications-latest-news-list/",
            "https://www.prnewswire.com/news-releases/policy-public-interest-latest-news/",
            "https://www.prnewswire.com/news-releases/policy-public-interest-latest-news/policy-public-interest-latest-news-list/",
            "https://www.prnewswire.com/il/news-releases/",
        ],
        collector_type="http",
        priority=3,
        notes="美通社_EN_科技综合新闻",
    ),

    # 47. GlobeNewswire
    Source(
        name="GlobeNewswire",
        category="投融资与生态",
        sub_category="PR新闻通讯社",
        urls=[
            "https://www.globenewswire.com/NewsRoom",
        ],
        collector_type="http",
        priority=3,
        notes="globenewswire_EN_新闻",
    ),

    # 48. NVIDIA GTC (same as NVIDIA)
    Source(
        name="NVIDIA GTC",
        category="投融资与生态",
        sub_category="生态大会",
        urls=[
            "https://developer.nvidia.com/blog",
            "https://blogs.nvidia.com/",
            "https://nvidianews.nvidia.com/news",
        ],
        collector_type="http",
        priority=3,
        notes="英伟达_Fabless_EN_博客新闻",
    ),

    # ─────────────────────────────────────────────────────
    # 七、政策与监管
    # ─────────────────────────────────────────────────────

    # 49. 欧盟AI Office
    Source(
        name="欧盟AI Office",
        category="政策与监管",
        sub_category="国际AI安全机构",
        urls=[
            "https://digital-strategy.ec.europa.eu/en/news",
        ],
        collector_type="http",
        priority=5,
        notes="欧盟Shaping Europe's digital future_国外政府_EN_新闻",
    ),

    # 50. 白宫科技政策办公室 (OSTP)
    Source(
        name="白宫OSTP",
        category="政策与监管",
        sub_category="美国政策来源",
        urls=[
            "https://www.whitehouse.gov/ostp/news-updates/",
            "https://www.whitehouse.gov/pcast/briefing-room/",
            "https://www.whitehouse.gov/ostp/news-updates/reports-and-documents/",
        ],
        collector_type="browser",
        priority=5,
        notes="美国白宫科技政策办公室OSTP_外国政府_EN_新闻及报告",
    ),

    # 51. NIST / 美国AISI
    Source(
        name="NIST",
        category="政策与监管",
        sub_category="美国政策来源",
        urls=[
            "https://www.nist.gov/news-events/news/search",
            "https://www.nist.gov/news-events/news-updates/search",
            "https://www.nist.gov/publications",
        ],
        collector_type="http",
        priority=4,
        notes="美国国家标准与技术研究院NIST_国外智库_EN_新闻报告",
    ),

    # 52. FTC (联邦贸易委员会)
    Source(
        name="FTC",
        category="政策与监管",
        sub_category="美国政策来源",
        urls=[
            "https://www.ftc.gov/news-events",
        ],
        collector_type="http",
        priority=4,
        notes="美国联邦贸易委员会FTC_EN_新闻",
    ),

    # 53. DOJ (司法部)
    Source(
        name="DOJ",
        category="政策与监管",
        sub_category="美国政策来源",
        urls=[
            "https://www.justice.gov/news/press-releases",
        ],
        collector_type="browser",
        priority=4,
        notes="美国司法部_外国政府_EN_发布(反爬，使用浏览器采集)",
    ),

    # 54. BIS (商务部工业与安全局)
    Source(
        name="BIS",
        category="政策与监管",
        sub_category="美国政策来源",
        urls=[
            "https://www.bis.gov/news-updates",
        ],
        collector_type="http",
        priority=5,
        notes="美国工业与安全局（BIS）_外国政府_EN_新闻",
    ),

    # 55. 国会研究服务处 (CRS)
    Source(
        name="CRS",
        category="政策与监管",
        sub_category="美国政策来源",
        urls=[
            "https://www.congress.gov/crs-products#/?termsToSearch=&orderBy=Date",
        ],
        collector_type="browser",
        priority=4,
        notes="美国国会服务局（CRS）_国外智库_EN_报告",
    ),

    # 56. GAO (政府问责办公室)
    Source(
        name="GAO",
        category="政策与监管",
        sub_category="美国政策来源",
        urls=[
            "https://www.gao.gov/press-center",
            "https://www.gao.gov/reports-testimonies",
        ],
        collector_type="http",
        priority=4,
        notes="美国政府问责局_外国政府_EN_报告",
    ),

    # 57. CHIPS.gov
    Source(
        name="CHIPS.gov",
        category="政策与监管",
        sub_category="美国政策来源",
        urls=[
            "https://www.nist.gov/chips/chips-news-releases",
        ],
        collector_type="http",
        priority=4,
    ),

    # 58. EU AI Act
    Source(
        name="EU AI Act",
        category="政策与监管",
        sub_category="欧盟政策来源",
        urls=[
            "https://digital-strategy.ec.europa.eu/en/news",
            "https://digital-strategy.ec.europa.eu/en/library",
        ],
        collector_type="http",
        priority=5,
        notes="欧盟Shaping Europe's digital future_国外政府_EN_新闻/报告",
    ),

    # 59. DSIT (英国科学、创新和技术部)
    Source(
        name="DSIT",
        category="政策与监管",
        sub_category="英国政策来源",
        urls=[
            "https://www.gov.uk/search/news-and-communications?organisations%5B%5D=council-for-science-and-technology&parent=council-for-science-and-technology",
        ],
        collector_type="browser",
        priority=4,
        notes="英国科学技术委员会_EN_科技新闻（改版，使用浏览器采集）",
    ),

    # 60. Georgetown CSET
    Source(
        name="Georgetown CSET",
        category="政策与监管",
        sub_category="AI政策智库",
        urls=[
            "https://cset.georgetown.edu/publications/",
            "https://cset.georgetown.edu/newsletters/",
            "https://cset.georgetown.edu/blog/",
        ],
        collector_type="http",
        priority=4,
        notes="美国安全与新兴技术中心（CSET）_国外智库_EN_出版物",
    ),

    # 61. CNAS
    Source(
        name="CNAS",
        category="政策与监管",
        sub_category="AI政策智库",
        urls=[
            "https://www.cnas.org/articles-multimedia?type=commentary",
            "https://www.cnas.org/reports/",
            "https://www.cnas.org/articles-multimedia?type=congressional-testimony",
            "https://www.cnas.org/press",
        ],
        collector_type="http",
        priority=4,
        notes="新美国安全中心（CNAS）_国外智库_EN_新闻与报告",
    ),

    # 62. RAND Corporation
    Source(
        name="RAND Corporation",
        category="政策与监管",
        sub_category="AI政策智库",
        urls=[
            "https://www.rand.org/pubs.html",
            "https://www.rand.org/news.html",
            "https://www.rand.org/pubs/research_reports.html",
        ],
        collector_type="http",
        priority=4,
        notes="兰德公司_国外智库_EN_报告博客新闻",
    ),

    # 63. GPAI / OECD
    Source(
        name="GPAI/OECD",
        category="政策与监管",
        sub_category="国际组织AI治理",
        urls=[
            "https://www.oecd.org/en/publications/reports.html?orderBy=mostRelevant&page=0",
            "https://www.oecd.org/en/publications/briefs.html?orderBy=mostRelevant&page=0",
            "https://www.oecd.org/en/search/publications.html?facetTags=oecd-content-types%3Apublications%2Freports%2Coecd-content-types%3Apublications%2Fpolicy-briefs%2Coecd-content-types%3Apublications%2Fpolicy-papers%2Coecd-content-types%3Apublications%2Fworking-papers%2Coecd-content-types%3Apublications%2Fpaper-series%2Coecd-content-types%3Apublications%2Fcase-studies%2Coecd-content-types%3Apublications%2Fbook-series&path=%2Fcontent%2Foecd%2Fen%2Fpublications&orderBy=mostRelevant&page=0",
        ],
        collector_type="http",
        priority=4,
        notes="经合组织_国际组织_EN_报告",
    ),

    # 64. 世界经济论坛
    Source(
        name="世界经济论坛",
        category="政策与监管",
        sub_category="国际组织AI治理",
        urls=[
            "https://cn.weforum.org/",
        ],
        collector_type="http",
        priority=4,
        notes="世界经济论坛_国际组织_CN_首页",
    ),

    # 65. ISO/IEC JTC 1/SC 42
    Source(
        name="ISO/IEC",
        category="政策与监管",
        sub_category="国际组织AI治理",
        urls=[
            "https://www.iso.org/insights",
            "https://www.iso.org/insights/standards-world",
        ],
        collector_type="http",
        priority=3,
        notes="国际标准化组织_行业组织_EN_观点新闻",
    ),

    # ─────────────────────────────────────────────────────
    # 八、专利与知识产权
    # ─────────────────────────────────────────────────────

    # 66. USPTO
    Source(
        name="USPTO",
        category="专利与知识产权",
        sub_category="专利数据库",
        urls=[
            "https://www.uspto.gov/ip-policy/economic-research/publications/reports",
        ],
        collector_type="http",
        priority=3,
        notes="美国专利商标局（USPTO）_国外智库_EN_报告",
    ),

    # 67. Clarivate Derwent
    Source(
        name="Clarivate Derwent",
        category="专利与知识产权",
        sub_category="专利数据库",
        urls=[
            "https://clarivate.com/news/",
        ],
        collector_type="http",
        priority=3,
        notes="科睿唯安_国外智库_EN_新闻",
    ),

    # ─────────────────────────────────────────────────────
    # 九、人才与劳动力
    # ─────────────────────────────────────────────────────

    # 68. WEF Future of Jobs
    Source(
        name="WEF Future of Jobs",
        category="人才与劳动力",
        sub_category="人才市场",
        urls=[
            "https://cn.weforum.org/",
        ],
        collector_type="http",
        priority=3,
        notes="世界经济论坛_国际组织_CN_中文首页",
    ),
]


def get_all_sources() -> list[Source]:
    """获取所有信息源"""
    return SOURCES


def get_sources_by_category(category: str) -> list[Source]:
    """按大类获取信息源"""
    return [s for s in SOURCES if s.category == category]


def get_source_categories() -> list[str]:
    """获取所有大类"""
    return list(dict.fromkeys(s.category for s in SOURCES))


def get_total_url_count() -> int:
    """获取URL总数"""
    return sum(len(s.urls) for s in SOURCES)


def get_unique_urls() -> set[str]:
    """获取去重后的URL集合"""
    urls = set()
    for s in SOURCES:
        for url in s.urls:
            urls.add(url.strip().rstrip(";"))
    return urls
