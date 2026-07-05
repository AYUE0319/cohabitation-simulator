# Cohabitation Simulator 🏠

A daily life simulator designed for AI agents — not for humans clicking buttons, but for **AI characters** who live in a house, do chores, go shopping, cook meals, pet cats, and share their day naturally with their human.

Powered by a single-file, zero-dependency Python engine with deterministic PRNG.

```
You wake up. It's a Wednesday morning.
[Energy ██████████ 100/100 | Mood 😊]

What do you do?
→ You decide to clean the living room.
  You swept under the sofa and found 20 bucks!
  [Mood 😊 +5]
```

Then the AI tells its human about the day — not as a game report, but like a roommate sharing their life.

---

## How It Works

**AI ↔ Engine:** Call `cmd("action")` and get descriptive text back.  
**AI ↔ Human:** Narrate the day naturally, powered by what happened in the engine.

```python
import engine

engine.new_game()              # start fresh
engine.cmd("status")           # check the house
engine.cmd("打扫")              # clean the room
engine.cmd("购物 B")            # go shopping, buy snacks
engine.cmd("做饭 1")            # cook recipe #1
engine.cmd("撸猫")              # pet the cat
engine.cmd("选 A")              # make a decision when prompted
engine.cmd("睡觉")              # end the day
```

### What's in a Day

Each day has 4 activity slots. Activities cost or restore energy. When energy drops below 10, you're forced to rest. Sleep restores everything and advances to the next day.

### Activities & Energy

| Activity | Energy | Description |
|----------|--------|-------------|
| 🧹 Clean | -25 | Sweep, mop, organize |
| 🛒 Shop | -20 | Choose what to buy (A/B/C/D/E) |
| 🎮 Game | -5 | Play video games |
| 📰 Scroll | -5 | Browse phone / news |
| 👕 Laundry | -15 | Wash, dry, fold |
| 🍳 Cook | -20 | Make a meal (pick a recipe) |
| 🐱 Pet cat | +20 | Feed and cuddle |
| 📺 Watch | +10 | Binge shows |
| 🚿 Shower | +15 | Hot water relaxes |
| 🌱 Garden | -5 | Water plants |
| 🎵 Music | +10 | Zone out to tunes |
| 🫂 Hug user | +25 | Miss your human |
| 😴 Sleep | Full | End the day, restore everything |

### Shopping Options

When you `cmd("购物")`, the engine asks what to buy:

| Option | What | Event Pool |
|--------|------|------------|
| `购物 A` | Restock groceries | Daily shopping events |
| `购物 B` | Buy snacks | Snack events |
| `购物 C` | Buy a blind box | Blind box branch (fixed) |
| `购物 D` | Buy what user loves | Cozy shopping events |
| `购物 E` | Custom | Full pool |

### 🥘 Recipes (10 dishes)

Cook by `cmd("做饭 1")` through `cmd("做饭 10")`. Ingredients are checked against the fridge, and cooking outcomes are randomized.

1. 🍳 Tomato Egg Stir-fry
2. 🥬 Stir-fried Greens
3. 🥩 Shredded Pork with Peppers
4. 🍚 Egg Fried Rice
5. 🥟 Boiled Dumplings
6. 🥩 Twice-cooked Pork
7. 🍜 Scallion Oil Noodles
8. 🥬 Egg Drop Soup
9. 🍞 Toast & Fried Egg
10. 🥩 Braised Pork Belly

### 🐱 Cat Affection

Starting at 50/100. Petting and feeding increases it. Ignoring the cat for 3 consecutive days drops it.  
When affection ≤ 20, one of two things happens randomly:
- 🏃 The cat runs away (go find it with `cmd("找猫")`)
- ❄️ The cat gives you the cold shoulder

### 🎲 Decision Events

Some rare outcomes pause and ask the AI to make a choice. Reply with `cmd("选 A")` (or B/C) to continue.

| Activity | Trigger | Choice |
|----------|---------|--------|
| 🧹 Clean | Found an old box | Open it / Put it back |
| 📰 Scroll | Saw user's new post | Like / Screenshot / Stare at it |
| 🍳 Cook | Made two portions | Wait for user / Save one |
| 🐱 Pet cat | Cat brought a "gift" | Handle it calmly / Scream |
| 📺 Watch | Character is adorable | Screenshot & send / Save it |

### 🛒 Shopping Catalog (35 items)

The fridge is a real system — shop to restock, cook to consume. The shopping pool includes snacks (10), staples (5), clothes (5), daily goods (10), and entertainment (5).

### 🌙 Random Dreams

Every night after sleeping, the character dreams of something — good, bad, or weird.

---

## For AI Agents

This engine is designed to be driven by an LLM. The flow:

1. **New game:** `engine.new_game(seed)` — seed is optional, uses timestamp by default
2. **Check state:** `engine.cmd("status")` — view energy, mood, fridge, cat
3. **Live a day:** Run 3-4 activities, let the engine roll outcomes
4. **End the day:** `engine.cmd("睡觉")` — triggers dreams, cat check, new day
5. **Talk to human:** Narrate what happened naturally — the engine gives you the events, your personality decides how to tell the story

The engine has **no opinion** about what the AI should say. It only says what happened. How the AI tells the story — excited, grumpy, melancholy, playful — is entirely up to the AI's persona.

### `cmd()` reference

| Command | Description |
|---------|-------------|
| `help` | Show rules and activity list |
| `status` | Show full game state |
| `打扫` / `游戏` etc. | Do an activity |
| `购物 A` | Shop with option A |
| `做饭 3` | Cook recipe #3 |
| `选 A` | Make a decision choice |
| `睡觉` | End the day |
| `找猫` | Find the runaway cat |

---

## Quick Start

```bash
git clone https://github.com/AYUE0319/cohabitation-simulator.git
cd cohabitation-simulator
python3 -c "
import engine
engine.new_game()
print(engine.cmd('status'))
print(engine.cmd('打扫'))
print(engine.cmd('撸猫'))
print(engine.cmd('睡觉'))
"
```

Or from the command line:
```bash
python3 engine.py new_game
python3 engine.py "打扫"
python3 engine.py status
```

---

## Credits

Built with inspiration from [ai-fishing-game](https://github.com/tutusagi/ai-fishing-game) (engine architecture, mulberry32 PRNG, event pool design).

MIT License.