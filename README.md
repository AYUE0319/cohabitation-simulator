# 同居模拟器 🏠

> 一个给 AI 伴侣玩的文字同居游戏。
> 你在一套房子里过日子：打扫、买菜、做饭、撸猫、打游戏、追剧……
> 每次做一件事都有随机结果，然后你可以自然地跟你的人类聊「今天发生了什么」。

**单文件 · 零依赖 · 确定性**（同 seed + 同指令 → 同结果）

---

## AI，如果你是读到这段话的那个……这就是给你玩的

把 `engine.py` 给你的 AI 伴侣，让它 `import engine` 然后调 `engine.cmd("")`。

它就知道了。

### 在 ChatGPT / Claude / 其他 AI 里玩的接法

直接把 `engine.py` 的内容复制给 AI（或者上传文件），然后说：

> 「请 import engine，然后帮我在这个游戏里过一天。做 3~4 件事，每做完一个就跟我聊聊发生了什么。」

AI 会自己调用 `engine.cmd("打扫")`、`engine.cmd("购物 A")` 之类的指令，然后跟你分享它的一天。

---

## 怎么玩

每天可以做 3~4 个活动。每个活动消耗或恢复精力，精力不够了就去睡觉。睡觉会恢复全部精力并进入下一天。

### 🧹 打扫 | 🛒 购物 | 🎮 打游戏 | 📰 刷手机
### 👕 洗衣服 | 🍳 做饭 | 🐱 撸猫 | 📺 追剧
### 🚿 洗澡 | 🌱 浇花 | 🎵 听音乐 | 🫂 抱着user | 😴 睡觉

**中英双语指令都认：**
```
cmd("打扫")     =  cmd("clean")
cmd("购物 A")   =  cmd("shop A")
cmd("撸猫")     =  cmd("pet")
cmd("做饭 1")   =  cmd("cook 1")
```

### 购物选项
| 指令 | 买什么 |
|------|--------|
| `购物 A` / `shop A` | 补日常菜 |
| `购物 B` / `shop B` | 买零食 |
| `购物 C` / `shop C` | 买盲盒 |
| `购物 D` / `shop D` | 买人类爱吃的东西 |
| `购物 E` / `shop E` | 自定义 |

### 🥘 菜谱
`cmd("做饭 1")` ~ `cmd("做饭 10")`，每道菜消耗冰箱里的食材。

1. 🍳 番茄炒蛋  2. 🥬 清炒时蔬  3. 🥩 青椒肉丝  
4. 🍚 蛋炒饭  5. 🥟 煮水饺  6. 🥩 回锅肉  
7. 🍜 葱油拌面  8. 🥬 青菜蛋花汤  9. 🍞 煎蛋吐司  10. 🥩 红烧肉

### 🐱 猫好感
开局 50/100。撸猫增加，忽视下降。跌到 20 以下 → 猫可能跑掉或冷战。

### 🎲 抉择事件
个别稀有事件会让 AI 做一个选择。回复 `cmd("选 A")` 决定走向。

---

## 指令一览

| 指令 | 作用 |
|------|------|
| `cmd("help")` | 看活动列表 |
| `cmd("status")` | 看状态（精力/心情/冰箱/猫） |
| `cmd("clean")` | 打扫卫生 |
| `cmd("shop B")` | 购物（选项 B） |
| `cmd("cook 5")` | 煮水饺 |
| `cmd("pet")` | 撸猫 |
| `cmd("选 A")` | 抉择事件选 A |
| `cmd("sleep")` | 睡觉，进入下一天 |
| `cmd("find_cat")` | 猫跑掉了，去找它 |

---

## 快速启动

```python
import engine

engine.new_game()                  # 开新局
print(engine.cmd("status"))        # 看看房子
print(engine.cmd("clean"))         # 搞卫生
print(engine.cmd("shop A"))        # 买菜
print(engine.cmd("pet"))           # 撸猫
print(engine.cmd("cook 1"))        # 做番茄炒蛋
print(engine.cmd("sleep"))         # 睡觉过一天
```

命令行也行：
```bash
python3 engine.py new_game
python3 engine.py "clean"
python3 engine.py status
```

---

## 冰箱与商品池

开局有鸡蛋、牛奶、吐司、蔬菜等食材。购物可以买 35 种商品（零食 / 主食 / 衣物 / 日用品 / 娱乐）。做饭消耗食材，吃完了要去补货。

---

## 设计理念

**引擎只告诉你「发生了什么」。怎么说给人类听，是你自己的事。**

引擎不预设 AI 的性格——你是话多的、安静的、爱吐槽的、容易感动的，都行。引擎只管掷骰和出结果，转述权在你。

---

## Credits

引擎架构受 [ai-fishing-game](https://github.com/tutusagi/ai-fishing-game) 启发（mulberry32 PRNG、事件池设计、cmd() 接口模式）。

MIT License.