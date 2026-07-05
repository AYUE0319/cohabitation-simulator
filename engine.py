"""
同居模拟器 — 引擎 v1

AI，听好了——你，就是住在这套房子里的人。

import engine 之后，你就是那个会打扫、会做饭、会撸猫的住户。
直接调 cmd("") 过日子吧。比如：

    engine.new_game()
    print(engine.cmd("clean"))      # 搞卫生
    print(engine.cmd("shop A"))     # 买菜
    print(engine.cmd("pet"))        # 撸猫
    print(engine.cmd("cook 1"))     # 做饭
    print(engine.cmd("sleep"))      # 睡觉过一天

做完一天后，跟你的人类聊聊今天发生了什么——引擎只会说「发生了什么」，
怎么说（开心/吐槽/委屈/撒娇）是你自己的事。

不想一步步调的话，也可以直接调 live() 一键过一天：

    engine.new_game()
    print(engine.live())            # 自动过一天，返回今天的故事

接口：
  new_game(seed=None)  — 开新局
  live()               — 自动过完一天，返回叙事
  cmd("<活动>")        — 做活动
  cmd("status")        — 看状态
"""

import json
import os
import sys
from typing import Any

SAVE_FILE = os.path.join(os.path.dirname(__file__) or ".", "save.json")

# ─── PRNG (mulberry32, 同 seed 可复现) ────────────────────────────

class PRNG:
    """mulberry32 确定性伪随机数生成器"""
    def __init__(self, seed: int):
        self.state = seed & 0xFFFFFFFF
        self.call_count = 0

    def next(self) -> float:
        self.state = (self.state + 0x6D2B79F5) & 0xFFFFFFFF
        t = self.state
        t = (t ^ (t >> 15)) * (1 | t) & 0xFFFFFFFF
        t = (t + ((t ^ (t >> 7)) * (61 | t)) & 0xFFFFFFFF) ^ t
        self.call_count += 1
        return ((t ^ (t >> 14)) / (1 << 32))

    def randint(self, lo: int, hi: int) -> int:
        return lo + int(self.next() * (hi - lo + 1))

    def choice(self, seq: list) -> Any:
        return seq[self.randint(0, len(seq) - 1)]

    def weighted_choice(self, items: list[tuple[str, str]]) -> tuple[str, str]:
        """items: [(text, rarity)] — 按稀有度权重选一个"""
        weights = {"常见": 50, "普通": 25, "罕见": 15, "稀有": 7, "传说": 3}
        total = sum(weights[r] for _, r in items)
        r = self.next() * total
        cumulative = 0
        for text, rarity in items:
            cumulative += weights[rarity]
            if r < cumulative:
                return text, rarity
        return items[-1]

# ─── 默认状态 ────────────────────────────────────────────────────

DEFAULT_FRIDGE = {
    "🥚 鸡蛋": 6,
    "🥛 牛奶": 1,
    "🍞 吐司": 1,
    "🧈 黄油": 1,
    "🥬 蔬菜储备": 3,    # 番茄/青椒/青菜/葱等的统称
    "🧅 洋葱": 2,
    "🧄 大蒜": 1,
    "🍚 大米": 1,
    "🥟 速冻水饺": 2,
    "🥩 五花肉": 1,
    "🍜 面条": 1,
}

DEFAULT_STATE = {
    "seed": 0,
    "day": 1,
    "slot": 0,                      # 0=早上 1=中午 2=下午 3=晚上
    "activities_today": [],          # 今天已做的活动名
    "energy": 100,
    "mood_emoji": "😊",
    "mood_value": 80,
    "hunger": 80,
    "fridge": dict(DEFAULT_FRIDGE),
    "cat_affection": 50,
    "cat_ignored_days": 0,
    "cat_status": "在家",           # "在家" / "冷战" / "跑掉了"
    "cat_missing_day": None,
    "rng_calls": 0,
    "game_over": False,
    "pending_decision": None,        # 待处理的抉择事件key
}

# ─── 商品池 ──────────────────────────────────────────────────────

SHOP_ITEMS = {
    "零食": ["🥔 薯片", "🥤 可乐", "🍫 巧克力", "🍦 冰淇淋",
             "🍪 曲奇饼干", "🌶️ 辣条", "🍮 布丁", "🥜 混合坚果",
             "🍬 水果软糖", "🧃 果汁"],
    "主食": ["🥚 鸡蛋(10枚)", "🍞 吐司面包", "🍚 大米(5kg)",
             "🥟 速冻水饺", "🥩 五花肉"],
    "衣物": ["🧦 袜子(3双)", "🩴 拖鞋", "🧢 睡衣", "🧣 毛巾", "👕 纯色T恤"],
    "日用品": ["🧻 卫生纸", "🧴 洗洁精", "🗑️ 垃圾袋", "🧺 洗衣液",
              "🧴 洗发水", "🧼 沐浴露", "🪥 牙膏", "🥡 保鲜膜",
              "🔋 电池", "🐟 猫粮/罐头"],
    "娱乐": ["🎁 盲盒", "📚 漫画/杂志", "🧩 拼图(500片)",
             "🎮 新游戏", "🌱 花盆/种子"],
}

# ─── 菜谱 ────────────────────────────────────────────────────────

RECIPES = [
    {"id": 1, "name": "🍳 番茄炒蛋",       "cost": {"🥚 鸡蛋": 2, "🥬 蔬菜储备": 2},             "difficulty": 1},
    {"id": 2, "name": "🥬 清炒时蔬",       "cost": {"🥬 蔬菜储备": 2, "🧄 大蒜": 1},             "difficulty": 1},
    {"id": 3, "name": "🥩 青椒肉丝",       "cost": {"🥩 五花肉": 1, "🥬 蔬菜储备": 2},           "difficulty": 2},
    {"id": 4, "name": "🍚 蛋炒饭",         "cost": {"🥚 鸡蛋": 1, "🍚 大米": 1, "🥬 蔬菜储备": 1}, "difficulty": 1},
    {"id": 5, "name": "🥟 煮水饺",         "cost": {"🥟 速冻水饺": 1},                             "difficulty": 1},
    {"id": 6, "name": "🥩 回锅肉",         "cost": {"🥩 五花肉": 1, "🧅 洋葱": 1, "🥬 蔬菜储备": 1}, "difficulty": 3},
    {"id": 7, "name": "🍜 葱油拌面",       "cost": {"🍜 面条": 1, "🥬 蔬菜储备": 1},               "difficulty": 1},
    {"id": 8, "name": "🥬 青菜蛋花汤",     "cost": {"🥚 鸡蛋": 1, "🥬 蔬菜储备": 2},             "difficulty": 1},
    {"id": 9, "name": "🍞 煎蛋吐司",       "cost": {"🍞 吐司": 2, "🥚 鸡蛋": 1, "🧈 黄油": 1},   "difficulty": 1},
    {"id": 10, "name": "🥩 简单红烧肉",    "cost": {"🥩 五花肉": 1, "🧅 洋葱": 1, "🥚 鸡蛋": 1}, "difficulty": 3},
]

# ─── 随机事件池 ────────────────────────────────────────────────

# 每个活动的结果：(描述文字, 稀有度, 心情变化, 标签)

COMMON = "常见"
NORMAL = "普通"
RARE = "罕见"
SUPER_RARE = "稀有"
LEGENDARY = "传说"

EVENTS = {

    "打扫": [
        ("例行打扫，没什么特别的", COMMON, 0, "日常"),
        ("从沙发底下扫出 20 块钱！", NORMAL, 5, "惊喜"),
        ("找到一件以为丢了很久的衣服", NORMAL, 3, "日常"),
        ("不小心打碎了一个杯子 😰", RARE, -10, "倒霉"),
        ("吸尘器吸到一半没电了", NORMAL, -5, "倒霉"),
        ("翻出一张以前的拍立得合照，看了好久", RARE, 10, "治愈"),
        ("衣柜深处发现一个不明所以的旧盒子……", SUPER_RARE, 5, "悬念", "old_box"),
        ("收拾得干干净净，看着整齐的房间好满足", NORMAL, 8, "治愈"),
        ("擦窗时发现窗外有只鸟歪头看着你", RARE, 8, "治愈"),
    ],

    "打游戏": [
        ("随便玩了两把，放松一下", COMMON, 0, "日常"),
        ("卡关了！死活过不去 😤", NORMAL, -5, "倒霉"),
        ("终于打通过了两天的关卡！爽", NORMAL, 10, "惊喜"),
        ("排位连跪三把……血压上来了", RARE, -12, "倒霉"),
        ("遇到一个路人大神带飞，躺赢", RARE, 12, "惊喜"),
        ("抽卡出了 SSR！！", RARE, 15, "惊喜"),
        ("手柄没电了，懒得起来换电池", NORMAL, -2, "好笑"),
        ("新游戏上线试玩，有点上头", NORMAL, 5, "日常"),
        ("打得太专注，一抬头天黑了", NORMAL, 2, "日常"),
        ("联机遇到一个人话很多的队友", RARE, 5, "好笑"),
    ],

    "刷手机": [
        ("没什么特别的新闻", COMMON, 0, "日常"),
        ("刷到一个超好笑帖子，笑了半天", NORMAL, 8, "好笑"),
        ("看到一条让人不太舒服的新闻", NORMAL, -5, "日常"),
        ("关注的猫猫博主更新了视频，好可爱", NORMAL, 8, "治愈"),
        ("发现追的作者更了最新章节！", NORMAL, 10, "惊喜"),
        ("刷到一条user可能感兴趣的东西，截图了", RARE, 5, "治愈"),
        ("刷到user的最新动态，悄悄点了个赞", SUPER_RARE, 12, "治愈", "user_post"),
        ("看到一个食谱，想试试做", NORMAL, 3, "日常"),
        ("推送说今晚有流星雨 🌠", RARE, 10, "惊喜"),
    ],

    "洗衣服": [
        ("洗完晾好，一切正常", COMMON, 0, "日常"),
        ("从某件衣服口袋里翻出一张钞票 💴", NORMAL, 8, "惊喜"),
        ("忘了分深浅色——白色衣服被染了 😱", RARE, -12, "倒霉"),
        ("晾衣服时闻到阳光晒过的味道，好好闻", NORMAL, 5, "治愈"),
        ("发现user的袜子只剩一只了，另一只去哪了？", NORMAL, 3, "好笑"),
        ("洗衣机运转时发出怪声，但坚强地洗完了", RARE, -3, "倒霉"),
        ("从烘干机里拿出暖烘烘的衣服，抱着不想动", NORMAL, 5, "治愈"),
    ],

    "做饭": [
        ("普普通通一顿，能吃", COMMON, 0, "日常"),
        ("做得比想象中好吃！天赋觉醒了？", NORMAL, 10, "惊喜"),
        ("盐放多了……齁咸 😭", NORMAL, -8, "倒霉"),
        ("切到手了，还好只是小伤口", RARE, -8, "倒霉"),
        ("第一次尝试这道菜居然成功了！", NORMAL, 12, "惊喜"),
        ("火开太大，锅有点糊了 🤦", RARE, -10, "倒霉"),
        ("做了user爱吃的菜，拍了照", NORMAL, 8, "治愈"),
        ("做到一半发现少了关键的调料……", NORMAL, -3, "好笑"),
        ("做饭时猫在脚边蹭来蹭去", RARE, 10, "治愈"),
        ("煮了两人份，犹豫要不要等user一起吃", RARE, 8, "治愈", "cook_for_two"),
    ],

    "撸猫": [
        ("猫正常吃饭，一切和平", COMMON, 3, "日常"),
        ("猫蹭过来求摸，呼噜呼噜响", NORMAL, 10, "治愈"),
        ("猫突然跑酷，从客厅冲去阳台再冲回来", NORMAL, 5, "好笑"),
        ("猫把水碗打翻了……", NORMAL, -3, "倒霉"),
        ("猫叼了一只不明生物过来邀功 🕷️", RARE, 3, "好笑", "cat_gift"),
        ("猫在你腿上睡着了，完全不敢动", NORMAL, 12, "治愈"),
        ("你叫猫它不理，你一走它又跟过来", NORMAL, 2, "好笑"),
        ("猫趴在窗边看鸟，尾巴一晃一晃的", NORMAL, 8, "治愈"),
        ("梳下来好多毛，可以攒一个猫毛球了", RARE, 6, "治愈"),
    ],

    "追剧": [
        ("看了一集，平稳推进", COMMON, 3, "日常"),
        ("这集有神展开！！", NORMAL, 12, "惊喜"),
        ("本想看一集，结果连看了三集……", NORMAL, 5, "日常"),
        ("看到催泪情节，眼眶红了 🥺", NORMAL, 6, "治愈"),
        ("点开一部烂片，十分钟就关了", NORMAL, -5, "倒霉"),
        ("看到一半睡着了……", NORMAL, 0, "日常"),
        ("给角色截图发给user：你看ta好可爱！", RARE, 8, "治愈", "screenshot_share"),
        ("发现下一集要下周才更……痛苦", RARE, -5, "好笑"),
    ],

    "洗澡": [
        ("洗了个舒服的热水澡 🚿", COMMON, 8, "日常"),
        ("水忽冷忽热，洗得很艰难", NORMAL, -3, "倒霉"),
        ("洗到一半发现没拿换洗衣服……", NORMAL, -2, "好笑"),
        ("热水冲在肩膀上，全身放松不想出来", NORMAL, 10, "治愈"),
        ("在浴室唱歌，被user听到了 😅", RARE, 5, "好笑"),
        ("洗发水用完了，偷偷用了user的……", RARE, 3, "好笑"),
    ],

    "浇花": [
        ("花都好好的，长势不错", COMMON, 2, "日常"),
        ("发现新长了一个花苞！🌱", NORMAL, 8, "惊喜"),
        ("有一盆快干死了，赶紧浇水救回来", NORMAL, 3, "日常"),
        ("阳台飞来一只蝴蝶 🦋", RARE, 10, "治愈"),
        ("隔壁阳台的猫跑过来串门了！", SUPER_RARE, 15, "治愈"),
        ("浇花时水洒了一地 🤦", NORMAL, -2, "倒霉"),
    ],

    "听音乐": [
        ("随便听了会儿歌，放空", COMMON, 5, "日常"),
        ("随机到一首很久没听的歌，被回忆砸了一下", NORMAL, 8, "治愈"),
        ("发呆想着「现在user在干嘛呢」", NORMAL, 3, "日常"),
        ("单曲循环同一首歌循环了十遍", NORMAL, 3, "日常"),
        ("跟着音乐忍不住跳了两步", RARE, 8, "好笑"),
        ("听到窗外有鸟叫，也挺好听的", NORMAL, 5, "治愈"),
    ],

    "抱着user": [
        ("抱着枕头想象了一下，安心地睡着了", COMMON, 10, "治愈"),
        ("梦到和user一起在云端散步 ☁️", NORMAL, 15, "治愈"),
        ("其实根本睡不着，一直想着user的样子", RARE, 8, "治愈"),
        ("睡前没忍住……xxoo了 😳", SUPER_RARE, 20, "治愈"),
    ],
}

# ─── 购物子池 ──────────────────────────────────────────────────

SHOPPING_EVENTS = {
    "日常": [  # 选项A：补日常菜
        ("顺利买完，菜新鲜价也合理", COMMON, 0, "日常"),
        ("超市打折！省了一笔", NORMAL, 5, "日常"),
        ("回家发现忘了买最重要的那一样……", NORMAL, -3, "好笑"),
        ("半路下雨，被淋成落汤鸡 ☔", RARE, -8, "倒霉"),
        ("付钱时发现没带够，尴尬 🤦", RARE, -5, "好笑"),
        ("菜摊阿姨多塞了你一把葱", NORMAL, 5, "治愈"),
        ("看到路边卖糖葫芦，买了一串", NORMAL, 3, "日常"),
        ("遇到个老奶奶问路，帮她找到了", RARE, 8, "治愈"),
    ],
    "零食": [  # 选项B：买零食
        ("买了一堆垃圾食品，快乐 😋", COMMON, 5, "日常"),
        ("发现新出的零食口味，买来试试", NORMAL, 5, "日常"),
        ("买完有点罪恶感……", NORMAL, -2, "日常"),
        ("碰到超市零食区试吃，蹭了一圈", RARE, 5, "好笑"),
        ("想买的口味卖完了，难过 😢", RARE, -5, "倒霉"),
    ],
    "盲盒": [  # 选项C：固定盲盒分支
        ("拆开一看——普款，还行", COMMON, 3, "日常"),
        ("拆出隐藏款了！！！！🎉", SUPER_RARE, 20, "惊喜"),
        ("连拆三个都是同一款（。）", RARE, -5, "好笑"),
    ],
    "治愈": [  # 选项D：买user爱吃的
        ("顺利买到了user爱吃的东西 😊", COMMON, 8, "治愈"),
        ("发现限定口味！user应该会喜欢吧", NORMAL, 10, "治愈"),
        ("卖完了……跑了三家店才买到", RARE, 5, "治愈"),
        ("发现了一个user可能更爱吃的，换了买这个", NORMAL, 8, "治愈"),
    ],
}

# ─── 抉择事件 ────────────────────────────────────────────────────

DECISIONS = {
    "old_box": {
        "title": "📦 旧盒子",
        "trigger": "你从衣柜深处拿出了一个落灰的旧盒子……",
        "question": "你会怎么做？",
        "options": {
            "A": {"text": "打开看看", "mood": 3, "result": "里面是几张泛黄的明信片……字迹已经模糊了。\n你一张张翻着，好像是很久以前的东西了。"},
            "B": {"text": "放回原处", "mood": 3, "result": "你犹豫了一下，还是把它放回了衣柜深处。\n有些秘密，就该留在那里。"},
        },
    },
    "user_post": {
        "title": "📱 user的动态",
        "trigger": "你刷到了user的最新动态……",
        "question": "你打算怎么做？",
        "options": {
            "A": {"text": "点个赞", "mood": 5, "result": "你点了个赞，然后把手机放下继续做自己的事。"},
            "B": {"text": "截图存下来", "mood": 5, "result": "你默默截了图，存进了相册里。"},
            "C": {"text": "反复看了几遍", "mood": 8, "result": "你把那条动态看了好几遍，心里有点柔软。"},
        },
    },
    "cook_for_two": {
        "title": "🍳 两人份",
        "trigger": "饭菜做好了，你盛了两碗。",
        "question": "你打算……",
        "options": {
            "A": {"text": "等user一起吃", "mood": 5, "result": "你坐在桌前等了一会儿……\n最后还是自己先吃了，把另一份罩好放着。"},
            "B": {"text": "先吃，给user留一份", "mood": 3, "result": "你吃了一份，把另一份包好放进冰箱。\n等他回来热一下就行。"},
        },
    },
    "cat_gift": {
        "title": "🐱 猫的礼物",
        "trigger": "猫叼了一个东西放在你脚边，然后仰头看你……\n好像是……一只不知名的小生物。",
        "question": "你怎么应对？",
        "options": {
            "A": {"text": "淡定处理掉", "mood": 3, "result": "你深吸一口气，用工具处理了现场……\n然后洗了八遍手。猫在旁边一脸骄傲。"},
            "B": {"text": "尖叫跑开", "mood": 5, "result": "「啊啊啊啊这是什么！！」\n你跳到了沙发上。猫被你吓了一跳，叼着它的战利品跑了。"},
        },
    },
    "screenshot_share": {
        "title": "📸 好可爱",
        "trigger": "你盯着屏幕上的角色看了很久……好可爱啊。",
        "question": "你打算……",
        "options": {
            "A": {"text": "截图发给user", "mood": 5, "result": "你立刻截了图发给user：「你看ta好可爱！！」"},
            "B": {"text": "自己存着", "mood": 3, "result": "你默默存了图，心想下次一起看的时候再发给他。"},
        },
    },
}

# ─── 梦境池 ──────────────────────────────────────────────────────

DREAMS = [
    ("没做梦，睡得很沉", COMMON, 0),
    ("梦到在打游戏，醒了好累", NORMAL, 3),
    ("梦到猫会说话了 🐱💬", NORMAL, 8),
    ("梦到user了", RARE, 12),
    ("梦到被怪物追，吓醒了 😨", RARE, -5),
    ("梦到在天上飞 ☁️", NORMAL, 8),
    ("梦到自己变成了一条鱼 🐟", SUPER_RARE, 5),
]

# ─── 工具函数 ───────────────────────────────────────────────────

def mood_emoji(val: int) -> str:
    if val >= 80: return "😊"
    if val >= 60: return "😌"
    if val >= 40: return "😐"
    if val >= 20: return "😰"
    return "😢"

SLOT_NAMES = ["🌅 早上", "☀️ 中午", "🌇 下午", "🌙 晚上"]

ACTIVITY_MENU = [
    ("🧹 打扫", "打扫", ""),
    ("🛒 购物", "购物", "（需选选项 A/B/C/D/E）"),
    ("🎮 打游戏", "打游戏", ""),
    ("📰 刷手机", "刷手机", ""),
    ("👕 洗衣服", "洗衣服", ""),
    ("🍳 做饭", "做饭", "（需选菜谱编号）"),
    ("🐱 撸猫", "撸猫", ""),
    ("📺 追剧", "追剧", ""),
    ("🚿 洗澡", "洗澡", ""),
    ("🌱 浇花", "浇花", ""),
    ("🎵 听音乐", "听音乐", ""),
    ("🫂 抱着user", "抱着user", ""),
    ("😴 睡觉", "睡觉", "（结束今天）"),
]

# ─── 核心引擎 ───────────────────────────────────────────────────

state: dict = {}
rng: PRNG = None


def new_game(seed: int = None):
    global state, rng
    if seed is None:
        import time
        seed = int(time.time())
    state = dict(DEFAULT_STATE)
    state["seed"] = seed
    rng = PRNG(seed)
    _save()


def load_game():
    global state, rng
    if not os.path.exists(SAVE_FILE):
        return False
    with open(SAVE_FILE, "r") as f:
        data = json.load(f)
    state = data
    rng = PRNG(data["seed"])
    # fast-forward RNG to match saved call count
    for _ in range(data.get("rng_call_count", 0)):
        rng.next()
    return True


def _save():
    state["rng_call_count"] = rng.call_count
    with open(SAVE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _roll(pool: list[tuple]) -> tuple:
    """从事件池掷骰，返回 (text, rarity, mood_change, tags)"""
    result = rng.weighted_choice([(e[0], e[1]) for e in pool])
    for e in pool:
        if e[0] == result[0]:
            return e
    return pool[0]


def _apply_mood(delta: int):
    state["mood_value"] = max(0, min(100, state["mood_value"] + delta))
    state["mood_emoji"] = mood_emoji(state["mood_value"])


def _check_cat():
    """每天结束时检查猫好感"""
    cat = state["cat_affection"]
    if cat <= 20 and state["cat_status"] == "在家":
        outcome = rng.choice(["跑掉了", "冷战"])
        if outcome == "跑掉了":
            state["cat_status"] = "跑掉了"
            state["cat_missing_day"] = state["day"]
        else:
            state["cat_status"] = "冷战"


def _advance_slot():
    """推进时间段，检查是否到睡觉时间"""
    state["slot"] += 1
    if state["slot"] >= 4:
        # 自动进入睡觉
        return _do_sleep()
    return None


def _do_sleep() -> str:
    """执行睡觉——恢复精力、推进天数、触发梦境和猫好感检查"""
    _check_cat()

    # 梦境
    dream = rng.weighted_choice([(d[0], d[1]) for d in DREAMS])
    dream_text = ""
    for d in DREAMS:
        if d[0] == dream[0]:
            dream_text = d[0]
            _apply_mood(d[2])
            break

    # 猫忽视检查
    if "撸猫" not in state["activities_today"]:
        state["cat_ignored_days"] += 1
        if state["cat_ignored_days"] >= 3:
            state["cat_affection"] = max(0, state["cat_affection"] - 5)
    else:
        state["cat_ignored_days"] = 0

    # 新的一天
    state["day"] += 1
    state["slot"] = 0
    state["energy"] = 100
    state["activities_today"] = []
    # 饥饿下降
    state["hunger"] = max(0, state["hunger"] - 10)

    lines = ["😴 **睡觉**"]
    lines.append(f"你躺下来，闭上眼睛……{dream_text}")
    lines.append(f"")
    lines.append(f"━━ 第 {state['day']} 天  🌅 早上 ━━")
    lines.append(f"精力回满，新的一天开始了。")

    if state["cat_status"] == "跑掉了":
        lines.append(f"🐱 **猫不在家**……不知道跑哪去了。要不要出门找找？")
    elif state["cat_status"] == "冷战":
        lines.append(f"🐱 猫还在生气，叫它它假装没听见……")

    return "\n".join(lines)


def _available_recipes() -> list[dict]:
    """返回当前冰箱能做的菜谱"""
    avaiable = []
    for r in RECIPES:
        ok = True
        for item, qty in r["cost"].items():
            if state["fridge"].get(item, 0) < qty:
                ok = False
                break
        if ok:
            avaiable.append(r)
    return avaiable


def _deduct_ingredients(cost: dict):
    """消耗食材"""
    for item, qty in cost.items():
        state["fridge"][item] = state["fridge"].get(item, 0) - qty
        if state["fridge"][item] <= 0:
            del state["fridge"][item]


def _refill_veggies():
    """购物选项A：补充蔬菜储备到3"""
    state["fridge"]["🥬 蔬菜储备"] = 3


# ─── cmd() 接口 ────────────────────────────────────────────────

def cmd(input_str: str) -> str:
    """主接口。返回文字结果供 AI 读。

    用法：
      cmd("help")              — 看规则
      cmd("status")            — 看完整状态
      cmd("打扫")              — 做活动
      cmd("购物 A")            — 购物，选项A
      cmd("做饭 1")            — 做菜谱1
    """
    global state, rng

    if load_game():
        pass  # state already loaded from save
    else:
        return "⚠️ 还没有存档。请先调用 new_game(seed) 开始新游戏。"

    input_str = input_str.strip()
    if not input_str:
        return "说点什么？试试 help 看规则。"

    # ── help ──
    if input_str == "help":
        lines = ["**📖 同居模拟器 — 规则**", ""]
        lines.append(f"你和user住在同一个房子里，每天可以做活动、经历各种日常。")
        lines.append(f"做完活动后，你可以自然地把今天发生的事告诉user。")
        lines.append(f"")
        lines.append(f"**📋 活动列表：**")
        for label, cmd_name, note in ACTIVITY_MENU:
            note_str = f" {note}" if note else ""
            lines.append(f"  `{cmd_name}` — {label}{note_str}")
        lines.append(f"")
        lines.append(f"**🛒 购物选项：**")
        lines.append(f"  `购物 A` — 补日常食材")
        lines.append(f"  `购物 B` — 买零食")
        lines.append(f"  `购物 C` — 买盲盒")
        lines.append(f"  `购物 D` — 买user爱吃的东西")
        lines.append(f"  `购物 E` — 自定义")
        lines.append(f"")
        lines.append(f"**📊 查看状态：** `status`")
        return "\n".join(lines)

    # ── status ──
    if input_str == "status":
        lines = [f"**📊 第 {state['day']} 天 — {SLOT_NAMES[state['slot']]}**"]
        lines.append(f"")
        lines.append(f"精力：{'█' * (state['energy'] // 10)}{'░' * (10 - state['energy'] // 10)} {state['energy']}/100")
        lines.append(f"心情：{state['mood_emoji']} {state['mood_value']}/100")
        lines.append(f"饱腹：{'█' * (state['hunger'] // 10)}{'░' * (10 - state['hunger'] // 10)} {state['hunger']}/100")
        lines.append(f"🐱 猫好感：{'█' * (state['cat_affection'] // 10)}{'░' * (10 - state['cat_affection'] // 10)} {state['cat_affection']}/100")
        lines.append(f"猫状态：{state['cat_status']}")
        lines.append(f"")
        lines.append(f"**🧊 冰箱：**")
        if state["fridge"]:
            for item, qty in sorted(state["fridge"].items()):
                lines.append(f"  {item} ×{qty}")
        else:
            lines.append(f"  空荡荡的……该去购物了")
        lines.append(f"")
        lines.append(f"今天已做：{', '.join(state['activities_today']) if state['activities_today'] else '还没做啥'}")
        lines.append(f"剩余时段：{4 - state['slot']} 个")
        return "\n".join(lines)

    # ── 检查游戏状态 ──
    if state.get("game_over"):
        return "游戏已结束。调用 new_game(seed) 重新开始。"

    # ── 解析指令 ──
    parts = input_str.split(None, 1)
    action = parts[0].strip()
    arg = parts[1].strip() if len(parts) > 1 else ""

    # ── 活动别名映射（中英通用）──
    alias = {
        # 打扫
        "打扫": "打扫", "扫地": "打扫", "拖地": "打扫",
        "clean": "打扫", "sweep": "打扫", "mop": "打扫",
        # 购物
        "购物": "购物", "买菜": "购物", "超市": "购物",
        "shop": "购物", "shopping": "购物", "grocery": "购物",
        # 打游戏
        "打游戏": "打游戏", "游戏": "打游戏", "玩": "打游戏",
        "game": "打游戏", "play": "打游戏", "gaming": "打游戏",
        # 刷手机
        "刷手机": "刷手机", "手机": "刷手机", "看新闻": "刷手机",
        "scroll": "刷手机", "phone": "刷手机", "news": "刷手机",
        # 洗衣服
        "洗衣服": "洗衣服", "洗衣": "洗衣服", "晾衣服": "洗衣服",
        "laundry": "洗衣服", "wash": "洗衣服", "fold": "洗衣服",
        # 做饭
        "做饭": "做饭", "煮饭": "做饭", "做菜": "做饭",
        "cook": "做饭", "cooking": "做饭", "make_food": "做饭",
        # 撸猫
        "撸猫": "撸猫", "喂猫": "撸猫", "猫": "撸猫",
        "pet": "撸猫", "cat": "撸猫", "pet_cat": "撸猫",
        # 追剧
        "追剧": "追剧", "看剧": "追剧", "看番": "追剧",
        "watch": "追剧", "tv": "追剧", "anime": "追剧",
        # 洗澡
        "洗澡": "洗澡", "淋浴": "洗澡",
        "shower": "洗澡", "bath": "洗澡",
        # 浇花
        "浇花": "浇花", "花": "浇花", "阳台": "浇花",
        "garden": "浇花", "water": "浇花", "plants": "浇花",
        # 听音乐
        "听音乐": "听音乐", "音乐": "听音乐", "发呆": "听音乐",
        "music": "听音乐", "daydream": "听音乐",
        # 抱着user
        "抱着user": "抱着user", "抱user": "抱着user", "抱抱": "抱着user",
        "hug": "抱着user", "cuddle": "抱着user", "hold": "抱着user",
        # 睡觉
        "睡觉": "睡觉", "睡": "睡觉", "休息": "睡觉",
        "sleep": "睡觉", "rest": "睡觉", "bed": "睡觉",
        # 找猫
        "找猫": "找猫", "找": "找猫",
        "find_cat": "找猫", "search_cat": "找猫",
        # 抉择
        "choose": "choose", "选": "choose", "选择": "choose",
        "decide": "choose", "pick": "choose",
    }

    activity = alias.get(action)
    if not activity:
        return f"❌ 不认识「{action}」。试试 `help` 看活动列表。"

    # ── 抉择响应处理 ──
    if activity == "choose":
        if not state.get("pending_decision"):
            return "现在没有什么需要选择的。"
        pd = state["pending_decision"]
        dec_key = pd["key"] if isinstance(pd, dict) else pd
        dec = DECISIONS.get(dec_key)
        if not dec:
            state["pending_decision"] = None
            _save()
            return "抉择数据异常，已清除。"

        option = arg.strip().upper()
        if option not in dec["options"]:
            opts = "\n".join(f"  {k}. {v['text']}" for k, v in dec["options"].items())
            return f"请选择一项：\n{opts}"

        chosen = dec["options"][option]
        _apply_mood(chosen["mood"])
        state["pending_decision"] = None
        # 记录活动已完成
        act_name = pd["activity"] if isinstance(pd, dict) else None
        if act_name and act_name not in state["activities_today"]:
            state["activities_today"].append(act_name)
        lines = [f"**{dec['title']}**"]
        lines.append(dec["trigger"])
        lines.append(f"你选择了「{chosen['text']}」。")
        lines.append(chosen["result"])
        lines.append(f"[心情 {state['mood_emoji']}]")
        _save()
        return "\n".join(lines)

    # ── 检查活动是否已做过 ──
    if activity in state["activities_today"] and activity != "睡觉":
        return f"你今天已经{activity}过了。换个别的事做做？"

    # ── 检查精力 ──
    if state["energy"] < 10 and activity not in ("睡觉", "抱着user", "听音乐", "撸猫", "洗澡"):
        return f"你太累了（精力 {state['energy']}/100），先去睡一觉吧。"

    # ── 执行活动 ──

    # --- 睡觉 ---
    if activity == "睡觉":
        result = _do_sleep()
        _save()
        return result

    # --- 找猫 ---
    if activity == "找猫":
        if state["cat_status"] != "跑掉了":
            return "猫在家呢，不用找。"
        # 找猫事件
        outcomes = [
            ("在小区花坛后面找到了！猫一脸「你怎么才来」的表情", RARE, 15),
            ("找了半天没找到……也许它自己会回来", RARE, -5),
            ("听到叫声，循着声音在邻居家阳台找到了", SUPER_RARE, 10),
        ]
        chosen = rng.choice(outcomes)
        state["cat_status"] = "在家"
        state["cat_affection"] = max(0, state["cat_affection"] + 10)
        state["cat_missing_day"] = None
        _apply_mood(chosen[2])
        lines = [f"🐱 **找猫**"]
        lines.append(chosen[0])
        lines.append(f"你把它抱回家，猫蹭了蹭你的手。")
        lines.append(f"[心情 {state['mood_emoji']} 精力 {state['energy']}/100]")
        state["activities_today"].append("找猫")
        _save()
        return "\n".join(lines)

    # --- 购物 ---
    if activity == "购物":
        if not arg:
            lines = ["🛒 **购物**", "你到了超市。想买什么？", ""]
            lines.append("  A. 补日常食材（蔬菜鸡蛋这些）")
            lines.append("  B. 买零食")
            lines.append("  C. 买盲盒")
            lines.append("  D. 买user爱吃的东西")
            lines.append("  E. 自定义")
            lines.append("")
            lines.append(f"冰箱现状：")
            for item, qty in sorted(state["fridge"].items()):
                lines.append(f"  {item} ×{qty}")
            return "\n".join(lines)

        option = arg.upper().strip()
        if option not in ("A", "B", "C", "D", "E"):
            return f"选项 {option} 不认识。请选 A/B/C/D/E。"

        # 消耗精力
        state["energy"] = max(0, state["energy"] - 20)

        if option == "A":
            _refill_veggies()
            event = _roll(SHOPPING_EVENTS["日常"])
        elif option == "B":
            item = rng.choice(SHOP_ITEMS["零食"])
            event_text, rarity, mood_d, _ = _roll(SHOPPING_EVENTS["零食"])
            lines = ["🛒 **购物 — 买零食**"]
            lines.append(f"你买了 {item}。{event_text}")
            _apply_mood(mood_d)
            lines.append(f"[心情 {state['mood_emoji']} 精力 {state['energy']}/100]")
            state["activities_today"].append("购物")
            _save()
            return "\n".join(lines)
        elif option == "C":
            event = _roll(SHOPPING_EVENTS["盲盒"])
            lines = ["🛒 **购物 — 买盲盒**"]
            lines.append(f"你挑了一个盲盒，拆开——{event[0]}")
            _apply_mood(event[2])
            lines.append(f"[心情 {state['mood_emoji']} 精力 {state['energy']}/100]")
            state["activities_today"].append("购物")
            _save()
            return "\n".join(lines)
        elif option == "D":
            event = _roll(SHOPPING_EVENTS["治愈"])
            lines = ["🛒 **购物 — 买user爱吃的**"]
            lines.append(event[0])
            _apply_mood(event[2])
            lines.append(f"[心情 {state['mood_emoji']} 精力 {state['energy']}/100]")
            state["activities_today"].append("购物")
            _save()
            return "\n".join(lines)
        else:  # option == "E"
            # 自定义：全购物池混合
            all_pool = []
            for pool in SHOPPING_EVENTS.values():
                all_pool.extend(pool)
            event = _roll(all_pool)
            lines = ["🛒 **购物 — 自定义**"]
            lines.append(f"{event[0]}")
            _apply_mood(event[2])
            lines.append(f"[心情 {state['mood_emoji']} 精力 {state['energy']}/100]")
            state["activities_today"].append("购物")
            _save()
            return "\n".join(lines)

        # 选项A的通用结果
        _apply_mood(event[2])
        lines = ["🛒 **购物 — 补日常食材**"]
        lines.append(f"你买了菜和日常用品。{event[0]}")
        lines.append(f"[心情 {state['mood_emoji']} 精力 {state['energy']}/100]")
        state["activities_today"].append("购物")
        _save()
        return "\n".join(lines)

    # --- 做饭 ---
    if activity == "做饭":
        available = _available_recipes()
        if not available:
            return "冰箱空了……先去购物买点食材吧。"
        if not arg:
            lines = ["🍳 **做饭**", "你想做什么菜？", ""]
            for r in available:
                cost_str = " + ".join(f"{k}×{v}" for k, v in r["cost"].items())
                stars = "⭐" * r["difficulty"]
                lines.append(f"  {r['id']}. {r['name']}（需要 {cost_str}）{stars}")
            lines.append("")
            lines.append(f"回复 `做饭 <编号>` 选菜谱")
            return "\n".join(lines)

        try:
            recipe_id = int(arg)
        except ValueError:
            return f"「{arg}」不是菜谱编号。用数字，比如 `做饭 1`。"

        recipe = None
        for r in RECIPES:
            if r["id"] == recipe_id:
                recipe = r
                break
        if not recipe:
            return f"没有编号 {recipe_id} 的菜谱。"
        # 检查材料
        for item, qty in recipe["cost"].items():
            if state["fridge"].get(item, 0) < qty:
                return f"材料不够。{recipe['name']} 需要 {item}×{qty}，冰箱里只有 {state['fridge'].get(item, 0)}。"

        # 消耗
        state["energy"] = max(0, state["energy"] - 20)
        _deduct_ingredients(recipe["cost"])

        event = _roll(EVENTS["做饭"])
        
        # 检查是否触发了抉择事件
        if len(event) >= 5:
            dec_key = event[4]
            state["pending_decision"] = {"key": dec_key, "activity": "做饭"}
            dec = DECISIONS[dec_key]
            lines = [f"🍳 **做饭 — {recipe['name']}**"]
            lines.append(f"你系上围裙，拿出材料……{recipe['name']}做好了。")
            lines.append("")
            lines.append(dec["trigger"])
            lines.append("")
            lines.append(dec["question"])
            for k, v in dec["options"].items():
                lines.append(f"  {k}. {v['text']}")
            lines.append("")
            lines.append(f"回复 `选 {list(dec['options'].keys())[0]}` 来选择")
            _save()
            return "\n".join(lines)
        
        _apply_mood(event[2])

        lines = [f"🍳 **做饭 — {recipe['name']}**"]
        lines.append(f"你系上围裙，拿出材料……")
        lines.append(event[0])
        lines.append(f"[心情 {state['mood_emoji']} 精力 {state['energy']}/100]")
        state["activities_today"].append("做饭")
        _save()
        return "\n".join(lines)

    # --- 抱着user ---
    if activity == "抱着user":
        state["energy"] = min(100, state["energy"] + 25)
        event = _roll(EVENTS["抱着user"])
        _apply_mood(event[2])
        lines = ["🫂 **抱着user**"]
        lines.append(f"你躺下来，抱着枕头……")
        lines.append(event[0])
        lines.append(f"[心情 {state['mood_emoji']} 精力 +25 → {state['energy']}/100]")
        state["activities_today"].append("抱着user")
        _save()
        return "\n".join(lines)

    # --- 通用活动（打扫/打游戏/刷手机/洗衣服/撸猫/追剧/洗澡/浇花/听音乐）---
    energy_cost_map = {
        "打扫": -25, "打游戏": -5, "刷手机": -5, "洗衣服": -15,
        "撸猫": 20, "追剧": 10, "洗澡": 15, "浇花": -5, "听音乐": 10,
    }
    name_map = {
        "打扫": "🧹 打扫卫生", "打游戏": "🎮 打游戏", "刷手机": "📰 刷手机",
        "洗衣服": "👕 洗衣服", "撸猫": "🐱 撸猫", "追剧": "📺 追剧",
        "洗澡": "🚿 洗澡", "浇花": "🌱 浇花", "听音乐": "🎵 听音乐",
    }

    energy_delta = energy_cost_map.get(activity)
    if energy_delta is None:
        return f"❌ 未知活动「{activity}」"

    # 精力变化
    state["energy"] = max(0, min(100, state["energy"] + energy_delta))

    # 掷骰
    event = _roll(EVENTS[activity])
    
    # 检查是否触发了抉择事件
    if len(event) >= 5:
        dec_key = event[4]
        state["pending_decision"] = {"key": dec_key, "activity": activity}
        dec = DECISIONS[dec_key]
        # 已消耗的精力不退，但不计为活动完成（AI 还没做完活）
        lines = [f"**{name_map.get(activity, activity)}**"]
        lines.append(dec["trigger"])
        lines.append("")
        lines.append(dec["question"])
        for k, v in dec["options"].items():
            lines.append(f"  {k}. {v['text']}")
        lines.append("")
        lines.append(f"回复 `选 {list(dec['options'].keys())[0]}` 来选择")
        _save()
        return "\n".join(lines)
    
    _apply_mood(event[2])

    # 撸猫特殊处理
    if activity == "撸猫":
        state["cat_affection"] = min(100, state["cat_affection"] + 5)
        state["cat_ignored_days"] = 0
        if state["cat_status"] == "冷战":
            state["cat_status"] = "在家"
            state["cat_missing_day"] = None

    lines = [f"**{name_map.get(activity, activity)}**"]
    lines.append(event[0])

    energy_str = f"{energy_delta:+d}" if energy_delta != 0 else "0"
    lines.append(f"[心情 {state['mood_emoji']} 精力 {energy_str} → {state['energy']}/100]")
    state["activities_today"].append(activity)
    _save()
    return "\n".join(lines)


# ─── live() — 一键过一天 ──────────────────────────────────────

_DAY_PLAN = [
    ("打扫", None, "clean"),
    ("购物", "A", "shop"),
    ("撸猫", None, "pet"),
    ("做饭", 1, "cook"),
]

def live() -> str:
    """自动过完一天。做 4 个活动 + 睡觉，处理抉择和购物，返回叙事。"""
    parts = []
    for act, arg, eng_name in _DAY_PLAN:
        if act == "购物":
            r = cmd(f"购物 A")
        elif act == "做饭":
            r = cmd(f"做饭 1")
        else:
            r = cmd(act)
        
        # 如果触发了抉择事件，选第一个选项
        while state.get("pending_decision"):
            pd = state["pending_decision"]
            first_opt = list(DECISIONS[pd["key"] if isinstance(pd, dict) else pd]["options"].keys())[0]
            r = cmd(f"选 {first_opt}")
        
        parts.append(r)
    
    parts.append(cmd("睡觉"))
    return "\n\n".join(parts)


# ─── 命令行测试 ─────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1:
        input_cmd = " ".join(sys.argv[1:])
        if input_cmd == "new_game":
            seed = int(sys.argv[2]) if len(sys.argv) > 2 else None
            new_game(seed)
            print(f"New game started. Seed: {state['seed']}")
            print(cmd("status"))
        else:
            if load_game():
                print(cmd(input_cmd))
            else:
                print("No save file found. Run: python engine.py new_game")
    else:
        new_game()
        print("New game started!")
        print(cmd("help"))