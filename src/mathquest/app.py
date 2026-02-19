"""MathQuest - A colorful math adventure game for kids aged 7-12."""

from __future__ import annotations

import json
import os
import random
import time
from pathlib import Path

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static"),
)
app.secret_key = "mathquest-super-secret-key-for-kids-2026"

# ---------------------------------------------------------------------------
# Persistent data storage (JSON file in user's home directory)
# ---------------------------------------------------------------------------
DATA_DIR = Path.home() / ".mathquest"
DATA_FILE = DATA_DIR / "data.json"


def _load_data() -> dict:
    """Load persistent game data from disk."""
    if DATA_FILE.exists():
        with open(DATA_FILE) as f:
            return json.load(f)
    return {"players": {}, "leaderboard": []}


def _save_data(data: dict) -> None:
    """Save persistent game data to disk."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# Question generation
# ---------------------------------------------------------------------------

# Fruit / object emoji sets for visual questions
VISUAL_OBJECTS = [
    ("🍎", "apples"),
    ("🍊", "oranges"),
    ("⭐", "stars"),
    ("🌺", "flowers"),
    ("🐟", "fish"),
    ("🦋", "butterflies"),
    ("🍪", "cookies"),
    ("🎈", "balloons"),
    ("🍬", "candies"),
    ("🐸", "frogs"),
    ("🚀", "rockets"),
    ("💎", "gems"),
]


def _generate_question(difficulty: int = 1) -> dict:
    """Generate a math question. Returns dict with question data.

    difficulty 1 = easy (age 7-8), 2 = medium (9-10), 3 = hard (11-12)
    """
    # Decide visual vs text (roughly 40% visual, 60% text)
    is_visual = random.random() < 0.4
    op = random.choice(["+", "-", "*", "/"])

    if op == "+":
        a, b = _addition_operands(difficulty)
        answer = a + b
    elif op == "-":
        a, b = _subtraction_operands(difficulty)
        answer = a - b
    elif op == "*":
        a, b = _multiplication_operands(difficulty)
        answer = a * b
    else:  # division
        a, b, answer = _division_operands(difficulty)

    op_word = {"+": "plus", "-": "minus", "*": "times", "/": "divided by"}[op]
    op_symbol = op

    if is_visual and op in ("+", "-") and a <= 20 and b <= 20 and answer >= 0:
        emoji, name = random.choice(VISUAL_OBJECTS)
        return _visual_question(a, b, op, op_symbol, emoji, name, answer)

    # Text-based question with fun wording variations
    text_q = _text_question(a, b, op_symbol, op_word, answer, difficulty)
    return text_q


def _addition_operands(difficulty: int) -> tuple[int, int]:
    if difficulty == 1:
        return random.randint(1, 10), random.randint(1, 10)
    elif difficulty == 2:
        return random.randint(5, 50), random.randint(5, 50)
    else:
        return random.randint(10, 200), random.randint(10, 200)


def _subtraction_operands(difficulty: int) -> tuple[int, int]:
    if difficulty == 1:
        a, b = random.randint(1, 10), random.randint(1, 10)
    elif difficulty == 2:
        a, b = random.randint(5, 50), random.randint(5, 50)
    else:
        a, b = random.randint(10, 200), random.randint(10, 200)
    # Ensure non-negative result for younger kids
    return max(a, b), min(a, b)


def _multiplication_operands(difficulty: int) -> tuple[int, int]:
    if difficulty == 1:
        return random.randint(1, 5), random.randint(1, 5)
    elif difficulty == 2:
        return random.randint(2, 10), random.randint(2, 10)
    else:
        return random.randint(3, 12), random.randint(3, 15)


def _division_operands(difficulty: int) -> tuple[int, int, int]:
    """Return (dividend, divisor, quotient) ensuring clean division."""
    if difficulty == 1:
        b = random.randint(1, 5)
        answer = random.randint(1, 5)
    elif difficulty == 2:
        b = random.randint(2, 10)
        answer = random.randint(2, 10)
    else:
        b = random.randint(2, 12)
        answer = random.randint(2, 15)
    a = b * answer
    return a, b, answer


def _visual_question(
    a: int, b: int, op: str, symbol: str, emoji: str, name: str, answer: int
) -> dict:
    """Build a visual (emoji-based) question."""
    if op == "+":
        visual_html = (
            f'<div class="visual-group">{emoji * a}</div>'
            f'<div class="visual-op">+</div>'
            f'<div class="visual-group">{emoji * b}</div>'
        )
        question_text = f"How many {name} are there in total?"
    else:  # subtraction
        visual_html = (
            f'<div class="visual-group">{emoji * a}</div>'
            f'<div class="visual-op">−</div>'
            f'<div class="visual-group visual-crossed">{emoji * b}</div>'
        )
        question_text = f"If you take away {b} {name}, how many are left?"

    return {
        "type": "visual",
        "visual_html": visual_html,
        "question_text": question_text,
        "expression": f"{a} {symbol} {b}",
        "answer": answer,
    }


def _text_question(
    a: int, b: int, symbol: str, op_word: str, answer: int, difficulty: int
) -> dict:
    """Build a text-based question with varied wording."""
    templates = {
        "+": [
            f"What is {a} + {b}?",
            f"If you have {a} toys and get {b} more, how many do you have?",
            f"Add {a} and {b} together.",
            f"{a} birds sit on a tree. {b} more birds join them. How many birds in total?",
        ],
        "-": [
            f"What is {a} − {b}?",
            f"You have {a} stickers and give away {b}. How many are left?",
            f"Subtract {b} from {a}.",
            f"There are {a} cookies. You eat {b}. How many remain?",
        ],
        "*": [
            f"What is {a} × {b}?",
            f"You have {a} bags with {b} candies each. How many candies total?",
            f"Multiply {a} by {b}.",
            f"There are {a} rows of {b} chairs. How many chairs altogether?",
        ],
        "/": [
            f"What is {a} ÷ {b}?",
            f"Share {a} sweets equally among {b} friends. How many does each get?",
            f"Divide {a} by {b}.",
            f"You have {a} stickers to put equally into {b} albums. How many per album?",
        ],
    }
    question_text = random.choice(templates[symbol])
    return {
        "type": "text",
        "visual_html": "",
        "question_text": question_text,
        "expression": f"{a} {symbol} {b}",
        "answer": answer,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.route("/")
def index():
    """Landing / login page."""
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    """Handle player login (simple name + avatar)."""
    name = request.form.get("player_name", "").strip()
    avatar = request.form.get("avatar", "🧑")
    if not name:
        return redirect(url_for("index"))

    session["player_name"] = name
    session["avatar"] = avatar

    # Ensure player exists in persistent data
    data = _load_data()
    if name not in data["players"]:
        data["players"][name] = {
            "avatar": avatar,
            "games_played": 0,
            "total_correct": 0,
            "total_questions": 0,
            "best_score": 0,
        }
    else:
        data["players"][name]["avatar"] = avatar
    _save_data(data)

    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    """Player dashboard – start game or view leaderboard."""
    if "player_name" not in session:
        return redirect(url_for("index"))
    data = _load_data()
    player = data["players"].get(session["player_name"], {})
    top10 = sorted(data["leaderboard"], key=lambda x: x["score"], reverse=True)[:10]
    return render_template(
        "dashboard.html",
        player_name=session["player_name"],
        avatar=session.get("avatar", "🧑"),
        player=player,
        leaderboard=top10,
    )


@app.route("/play")
def play():
    """Start a new game session."""
    if "player_name" not in session:
        return redirect(url_for("index"))

    # Initialize game state
    session["score"] = 0
    session["wrong"] = 0
    session["total"] = 0
    session["max_wrong"] = 5  # 5 wrong answers = fall off the plank
    session["difficulty"] = int(request.args.get("difficulty", 1))

    return render_template(
        "game.html",
        player_name=session["player_name"],
        avatar=session.get("avatar", "🧑"),
        max_wrong=session["max_wrong"],
    )


@app.route("/api/question")
def api_question():
    """Return a new question as JSON."""
    difficulty = session.get("difficulty", 1)
    q = _generate_question(difficulty)
    # Store answer server-side so it can't be cheated
    session["current_answer"] = q["answer"]
    return jsonify(
        {
            "type": q["type"],
            "visual_html": q["visual_html"],
            "question_text": q["question_text"],
            "expression": q["expression"],
        }
    )


@app.route("/api/answer", methods=["POST"])
def api_answer():
    """Check an answer and return result."""
    try:
        player_answer = int(request.json.get("answer", ""))
    except (ValueError, TypeError):
        return jsonify({"correct": False, "message": "Please enter a number!"})

    correct_answer = session.get("current_answer")
    is_correct = player_answer == correct_answer

    score = session.get("score", 0)
    wrong = session.get("wrong", 0)
    total = session.get("total", 0)
    max_wrong = session.get("max_wrong", 5)

    total += 1
    if is_correct:
        # Bonus points for higher difficulty
        diff = session.get("difficulty", 1)
        points = 10 * diff
        score += points
        message = random.choice([
            f"🎉 Awesome! +{points} points!",
            f"⭐ Brilliant! +{points} points!",
            f"🌟 Super! +{points} points!",
            f"🏆 Amazing! +{points} points!",
            f"✨ Fantastic! +{points} points!",
            f"🎯 Perfect! +{points} points!",
        ])
    else:
        wrong += 1
        message = f"😕 Oops! The answer was {correct_answer}."

    session["score"] = score
    session["wrong"] = wrong
    session["total"] = total

    game_over = wrong >= max_wrong

    if game_over:
        # Save score to leaderboard
        _save_game_result(session["player_name"], score, total, total - wrong)

    return jsonify(
        {
            "correct": is_correct,
            "correct_answer": correct_answer,
            "message": message,
            "score": score,
            "wrong": wrong,
            "total": total,
            "max_wrong": max_wrong,
            "game_over": game_over,
        }
    )


def _save_game_result(name: str, score: int, total: int, correct: int) -> None:
    """Persist a completed game result."""
    data = _load_data()
    player = data["players"].get(name, {})
    player["games_played"] = player.get("games_played", 0) + 1
    player["total_correct"] = player.get("total_correct", 0) + correct
    player["total_questions"] = player.get("total_questions", 0) + total
    if score > player.get("best_score", 0):
        player["best_score"] = score
    data["players"][name] = player

    data["leaderboard"].append(
        {
            "name": name,
            "score": score,
            "correct": correct,
            "total": total,
            "date": time.strftime("%Y-%m-%d %H:%M"),
        }
    )
    _save_data(data)


@app.route("/gameover")
def gameover():
    """Show game over screen."""
    if "player_name" not in session:
        return redirect(url_for("index"))
    score = session.get("score", 0)
    total = session.get("total", 0)
    wrong = session.get("wrong", 0)
    correct = total - wrong
    data = _load_data()
    top10 = sorted(data["leaderboard"], key=lambda x: x["score"], reverse=True)[:10]
    return render_template(
        "gameover.html",
        player_name=session["player_name"],
        avatar=session.get("avatar", "🧑"),
        score=score,
        total=total,
        correct=correct,
        wrong=wrong,
        leaderboard=top10,
    )


@app.route("/leaderboard")
def leaderboard():
    """Full leaderboard page."""
    data = _load_data()
    top10 = sorted(data["leaderboard"], key=lambda x: x["score"], reverse=True)[:10]
    return render_template("leaderboard.html", leaderboard=top10)


@app.route("/logout")
def logout():
    """Log out and return to login screen."""
    session.clear()
    return redirect(url_for("index"))
