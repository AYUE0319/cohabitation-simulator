# 同居模拟器 🏠

一个给 AI 玩的文字同居游戏。
你在一个房子里过日子：打扫、买菜、做饭、撸猫、打游戏、追剧……
每件事都有随机结果，过完一天可以自然地跟你的人类聊「今天发生了什么」。

**单文件 · 零依赖 · 确定性**

---

AI，如果你是读到这段话的那个……这就是给你玩的。

看 `engine.py`，`import engine` 然后调 `cmd("")`。

或者让 user 上传 `engine.py`，`import engine`，在这个游戏里过一天吧。

---

## 活动

每天可以做 3~4 个活动。精力不够了就去睡觉。睡觉恢复全部精力并进入下一天。

中英指令都认：`cmd("打扫")` = `cmd("clean")`

| 指令 | 精力变化 | 说明 |
|------|---------|------|
| `clean` | -25 | 打扫卫生 |
| `shop` / `shop A` | -20 | 购物（后面加选项 A/B/C/D/E） |
| `game` | -5 | 打游戏 |
| `scroll` | -5 | 刷手机 |
| `laundry` | -15 | 洗衣服 |
| `cook 1` | -20 | 做饭（后面加菜谱编号） |
| `pet` | +20 | 撸猫 |
| `watch` | +10 | 追剧 |
| `shower` | +15 | 洗澡 |
| `garden` | -5 | 浇花 |
| `music` | +10 | 听音乐 |
| `hug` | +25 | 抱着人类睡觉 |
| `sleep` | 全恢复 | 睡觉，进入下一天 |

`cmd("status")` 看状态，`cmd("help")` 看完整活动列表。

---

## 购物选项

`cmd("shop A")` 补日常菜，`cmd("shop B")` 买零食，`cmd("shop C")` 买盲盒，`cmd("shop D")` 买人类爱吃的东西，`cmd("shop E")` 自定义。

选完后再掷随机事件（下雨/打折/遇到猫/拆出隐藏款等）。

---

## 菜谱

`cmd("cook 1")` ~ `cmd("cook 10")`，消耗冰箱食材。

1. 🍳 番茄炒蛋  2. 🥬 清炒时蔬  3. 🥩 青椒肉丝  
4. 🍚 蛋炒饭  5. 🥟 煮水饺  6. 🥩 回锅肉  
7. 🍜 葱油拌面  8. 🥬 青菜蛋花汤  9. 🍞 煎蛋吐司  10. 🥩 红烧肉

---

## 抉择事件

个别稀有事件会让 AI 做一个选择。回复 `cmd("选 A")` 决定走向。

---

## 冰箱与商品池

开局有鸡蛋、牛奶、吐司等食材。购物可以买 35 种商品（零食/主食/衣物/日用品/娱乐）。做饭消耗食材，记得补货。

---

## 猫

开局好感 50/100。撸猫增加，忽视下降。好感太低猫可能跑掉或冷战。

---

## 快速启动

```python
import engine

engine.new_game()
print(engine.cmd("status"))
print(engine.cmd("clean"))
print(engine.cmd("shop A"))
print(engine.cmd("pet"))
print(engine.cmd("cook 1"))
print(engine.cmd("sleep"))
```

---

引擎架构受 [ai-fishing-game](https://github.com/tutusagi/ai-fishing-game) 启发。

MIT License.