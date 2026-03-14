"""MathQuest - A colorful math adventure game for kids aged 6-14."""

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


# ---------------------------------------------------------------------------
# Question ranges keyed by (age_group, sub_difficulty)
# age_group:     1=6-8, 2=9-10, 3=11-12, 4=13-14
# sub_difficulty: 1=easy, 2=medium, 3=hard
# Tuple layout: (num_min, num_max, mult_max, div_b_max, div_q_max)
# ---------------------------------------------------------------------------
_RANGES: dict[tuple[int, int], tuple[int, int, int, int, int]] = {
    (1, 1): (1, 5, 3, 2, 3),  # 6-8  easy
    (1, 2): (1, 10, 5, 3, 5),  # 6-8  medium
    (1, 3): (2, 15, 6, 5, 6),  # 6-8  hard
    (2, 1): (5, 20, 8, 5, 8),  # 9-10 easy
    (2, 2): (10, 50, 10, 8, 10),  # 9-10 medium
    (2, 3): (20, 100, 12, 10, 12),  # 9-10 hard
    (3, 1): (20, 100, 12, 10, 15),  # 11-12 easy
    (3, 2): (50, 200, 15, 12, 15),  # 11-12 medium
    (3, 3): (100, 500, 20, 15, 20),  # 11-12 hard
    (4, 1): (100, 500, 20, 15, 20),  # 13-14 easy
    (4, 2): (200, 1000, 25, 20, 25),  # 13-14 medium
    (4, 3): (500, 2000, 50, 25, 50),  # 13-14 hard
}


def _generate_question(age_group: int = 1, sub_difficulty: int = 1) -> dict:
    """Generate a math question.

    age_group:      1=ages 6-8, 2=9-10, 3=11-12, 4=13-14
    sub_difficulty: 1=easy, 2=medium, 3=hard
    """
    num_min, num_max, mult_max, div_b_max, div_q_max = _RANGES[
        (age_group, sub_difficulty)
    ]

    is_visual = random.random() < 0.4
    op = random.choice(["+", "-", "*", "/"])

    if op == "+":
        a = random.randint(num_min, num_max)
        b = random.randint(num_min, num_max)
        answer = a + b
    elif op == "-":
        a = random.randint(num_min, num_max)
        b = random.randint(num_min, num_max)
        a, b = max(a, b), min(a, b)
        answer = a - b
    elif op == "*":
        a = random.randint(1, mult_max)
        b = random.randint(1, mult_max)
        answer = a * b
    else:  # division – always clean
        b = random.randint(1, div_b_max)
        answer = random.randint(1, div_q_max)
        a = b * answer

    op_symbol = op

    if is_visual and op in ("+", "-") and a <= 20 and b <= 20 and answer >= 0:
        emoji, name = random.choice(VISUAL_OBJECTS)
        return _visual_question(a, b, op, op_symbol, emoji, name, answer)

    q = _text_question(a, b, op_symbol, answer, age_group)

    # ~25% of non-visual questions become multiple choice
    if random.random() < 0.25:
        distractors = _generate_distractors(answer)
        choices = distractors + [answer]
        random.shuffle(choices)
        q["type"] = "multiple_choice"
        q["choices"] = choices
    else:
        q["choices"] = []

    return q


def _generate_distractors(answer: int, n: int = 3) -> list[int]:
    """Generate n plausible wrong answers that are close but distinct."""
    mag = max(1, abs(answer))
    if mag <= 10:
        offsets = [1, 2, 3, 4, 5]
    elif mag <= 50:
        offsets = [1, 2, 3, 5, 10]
    elif mag <= 200:
        offsets = [5, 10, 15, 20, 25]
    elif mag <= 1000:
        offsets = [10, 25, 50, 75, 100]
    else:
        offsets = [50, 100, 150, 200, 250]

    distractors: set[int] = set()
    random.shuffle(offsets)
    for off in offsets:
        for sign in (1, -1):
            candidate = answer + sign * off
            if candidate > 0 and candidate != answer:
                distractors.add(candidate)
                if len(distractors) == n:
                    break
        if len(distractors) == n:
            break

    # Last-resort fallback
    step = 1
    while len(distractors) < n:
        candidate = answer + step
        if candidate != answer and candidate > 0:
            distractors.add(candidate)
        step += 1

    return list(distractors)[:n]


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
        "choices": [],
    }


# ---------------------------------------------------------------------------
# Age-appropriate question templates
# Each age group has 5-6 templates per operator (20-24 per group).
# ---------------------------------------------------------------------------
_QUESTION_TEMPLATES: dict[int, dict[str, list[str]]] = {
    1: {  # Ages 6-8 – simple, concrete, emoji-friendly language
        "+": [
            "What is {a} + {b}?",
            "You have {a} apples and your friend gives you {b} more. How many apples do you have now?",
            "There are {a} red balloons and {b} blue balloons. How many balloons are there altogether?",
            "{a} frogs are sitting on a lily pad. {b} more frogs jump on. How many frogs are there now?",
            "You eat {a} grapes and then eat {b} more. How many grapes did you eat in total?",
            "{a} butterflies are on a flower and {b} more fly over. How many butterflies is that altogether?",
        ],
        "-": [
            "What is {a} − {b}?",
            "You have {a} sweets and you eat {b}. How many sweets are left?",
            "There are {a} ducks in a pond. {b} ducks swim away. How many ducks are still in the pond?",
            "You had {a} stickers but gave {b} to your friend. How many stickers do you have left?",
            "{a} birds are sitting on a branch. {b} fly away. How many birds are still on the branch?",
            "A jar has {a} biscuits. You take out {b}. How many biscuits are left in the jar?",
        ],
        "*": [
            "What is {a} × {b}?",
            "There are {a} bags with {b} sweets in each one. How many sweets are there altogether?",
            "{a} children each have {b} pencils. How many pencils is that in total?",
            "You have {a} boxes with {b} toy cars in each. How many toy cars do you have altogether?",
            "There are {a} rows of flowers in a garden. Each row has {b} flowers. How many flowers are there?",
            "{a} friends each pick {b} strawberries. How many strawberries did they pick altogether?",
        ],
        "/": [
            "What is {a} ÷ {b}?",
            "Share {a} sweets equally between {b} friends. How many sweets does each friend get?",
            "{a} apples are shared equally into {b} bowls. How many apples are in each bowl?",
            "You have {a} stickers to share equally among {b} friends. How many does each friend get?",
            "There are {a} crayons to share equally between {b} children. How many crayons does each child get?",
            "{a} biscuits are put equally onto {b} plates. How many biscuits are on each plate?",
        ],
    },
    2: {  # Ages 9-10 – slightly larger numbers, school and everyday contexts
        "+": [
            "What is {a} + {b}?",
            "A school has {a} children in Year 4 and {b} in Year 5. How many children is that altogether?",
            "In a football match, one team brings {a} supporters and the other brings {b}. How many supporters in total?",
            "A bookshop sells {a} books in the morning and {b} books in the afternoon. How many books is that altogether?",
            "Marcus saves £{a} in January and £{b} in February. How much has he saved in total?",
            "A park has {a} oak trees and {b} pine trees. How many trees are there in total?",
        ],
        "-": [
            "What is {a} − {b}?",
            "A bag holds {a} marbles. {b} marbles fall out. How many marbles are left?",
            "A school play has {a} tickets. {b} tickets are sold. How many tickets are still unsold?",
            "A library has {a} books. {b} are borrowed. How many books remain on the shelves?",
            "A shop had {a} items in stock. After selling {b}, how many items are left?",
            "A swimming pool holds {a} litres. {b} litres leak out. How many litres remain?",
        ],
        "*": [
            "What is {a} × {b}?",
            "{a} children each bring {b} sandwiches to a picnic. How many sandwiches are there in total?",
            "A shop sells boxes of {b} pencils. If {a} boxes are bought, how many pencils is that?",
            "There are {a} rows of chairs in a hall, with {b} chairs in each row. How many chairs are there altogether?",
            "Each book has {b} chapters. How many chapters are in {a} books?",
            "A minibus carries {b} passengers. How many passengers can {a} minibuses carry?",
        ],
        "/": [
            "What is {a} ÷ {b}?",
            "{a} children are split equally into {b} teams. How many children are in each team?",
            "A baker makes {a} rolls and packs them equally into {b} boxes. How many rolls are in each box?",
            "£{a} is shared equally between {b} friends. How much does each friend receive?",
            "{a} stickers are shared equally across {b} pages of a sticker book. How many stickers per page?",
            "A farmer plants {a} seeds equally across {b} rows. How many seeds are in each row?",
        ],
    },
    3: {  # Ages 11-12 – real-world contexts, slightly abstract
        "+": [
            "What is {a} + {b}?",
            "A cinema sold {a} tickets on Saturday and {b} on Sunday. What was the total number of tickets sold?",
            "A runner completed {a} metres on the first lap and {b} metres on the second. How far did they run in total?",
            "An online shop received {a} orders on Monday and {b} orders on Tuesday. How many orders is that altogether?",
            "A fundraiser raised £{a} in the morning and £{b} in the afternoon. How much was raised in total?",
            "In a survey, {a} students prefer science and {b} prefer English. How many students is that in total?",
        ],
        "-": [
            "What is {a} − {b}?",
            "A charity started with £{a} and spent £{b} on supplies. How much money does the charity have left?",
            "A train journey is {a} km long. After having travelled {b} km, how far is still remaining?",
            "A theatre has {a} seats. {b} seats are occupied. How many seats are empty?",
            "A warehouse stored {a} boxes. {b} boxes were dispatched. How many boxes remain in the warehouse?",
            "A school raised {a} points in a competition. After a penalty of {b} points, how many points do they have?",
        ],
        "*": [
            "What is {a} × {b}?",
            "A factory produces {b} items every hour. How many items are produced in {a} hours?",
            "A garden centre sells trees for £{b} each. What is the total cost of {a} trees?",
            "A school trip costs £{b} per student. What is the total cost for {a} students?",
            "A car travels at {b} km/h. How far does it travel in {a} hours?",
            "Each shelf in a library holds {b} books. How many books can {a} shelves hold?",
        ],
        "/": [
            "What is {a} ÷ {b}?",
            "A school trip costs £{a} in total, shared equally between {b} students. How much does each student pay?",
            "A road of {a} km is divided into {b} equal sections for resurfacing. How long is each section?",
            "{a} eggs are packed equally into {b} trays. How many eggs are in each tray?",
            "{a} minutes of PE is split equally into {b} activities. How many minutes is each activity?",
            "A prize fund of £{a} is split equally between {b} winners. How much does each winner receive?",
        ],
    },
    4: {  # Ages 13-14 – abstract, professional, and analytical contexts
        "+": [
            "What is {a} + {b}?",
            "A company made a profit of £{a} in March and £{b} in April. What was the combined profit?",
            "An athlete ran {a} metres in the first heat and {b} metres in the second. What is the total distance?",
            "Two survey groups had {a} and {b} respondents respectively. What was the total sample size?",
            "An investment portfolio grew by £{a} in year one and £{b} in year two. What is the total growth?",
            "A project used {a} hours of development time and {b} hours of testing. What was the total time?",
        ],
        "-": [
            "What is {a} − {b}?",
            "An annual budget is £{a} and expenditure so far is £{b}. What is the remaining budget?",
            "Population A is {a} and population B is {b}. What is the difference between the two populations?",
            "A share was valued at £{a} and then fell by £{b}. What is its new value?",
            "A manufacturer produced {a} units and {b} were found to be faulty. How many acceptable units were produced?",
            "A reservoir contains {a} megalitres. After a drought it lost {b} megalitres. How much remains?",
        ],
        "*": [
            "What is {a} × {b}?",
            "A machine produces {b} units per minute. How many units are produced in {a} minutes?",
            "A consultant charges £{b} per hour. What is the total fee for {a} hours of work?",
            "A rectangular plot measures {a} metres by {b} metres. What is its area in square metres?",
            "A product sells for £{b} per unit. What is the total revenue from {a} units sold?",
            "A data file stores {b} bytes per record. What is the total size in bytes for {a} records?",
        ],
        "/": [
            "What is {a} ÷ {b}?",
            "A total project cost of £{a} is divided equally among {b} departments. What is each department's share?",
            "A dataset of {a} entries is divided into {b} equal groups for analysis. How many entries are in each group?",
            "A {a} km pipeline is split into {b} equal sections for maintenance. How long is each section in km?",
            "A survey of {a} people is divided into {b} equal focus groups. How many people are in each group?",
            "A storage facility of {a} square metres is divided equally into {b} units. What is the size of each unit?",
        ],
    },
}


def _text_question(
    a: int, b: int, symbol: str, answer: int, age_group: int
) -> dict:
    """Return a randomly chosen age-appropriate text question."""
    template = random.choice(_QUESTION_TEMPLATES[age_group][symbol])
    question_text = template.format(a=a, b=b)
    return {
        "type": "text",
        "visual_html": "",
        "question_text": question_text,
        "expression": f"{a} {symbol} {b}",
        "answer": answer,
        "choices": [],
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
    top10 = sorted(
        data["leaderboard"], key=lambda x: x["score"], reverse=True
    )[:10]
    return render_template(
        "dashboard.html",
        player_name=session["player_name"],
        avatar=session.get("avatar", "🧑"),
        player=player,
        leaderboard=top10,
    )


@app.route("/choose-difficulty")
def choose_difficulty():
    """Intermediate screen – pick Easy / Medium / Hard within an age group."""
    if "player_name" not in session:
        return redirect(url_for("index"))
    age_group = int(request.args.get("age_group", 1))
    age_labels = {1: "6–8", 2: "9–10", 3: "11–12", 4: "13–14"}
    return render_template(
        "choose_difficulty.html",
        player_name=session["player_name"],
        avatar=session.get("avatar", "🧑"),
        age_group=age_group,
        age_label=age_labels.get(age_group, str(age_group)),
    )


@app.route("/play")
def play():
    """Start a new game session."""
    if "player_name" not in session:
        return redirect(url_for("index"))

    age_group = int(request.args.get("age_group", 1))
    sub_difficulty = int(request.args.get("sub_difficulty", 1))

    # Initialize game state
    session["score"] = 0
    session["wrong"] = 0
    session["total"] = 0
    session["max_wrong"] = 5  # 5 wrong answers = game over
    session["age_group"] = age_group
    session["sub_difficulty"] = sub_difficulty

    return render_template(
        "game.html",
        player_name=session["player_name"],
        avatar=session.get("avatar", "🧑"),
        max_wrong=session["max_wrong"],
    )


@app.route("/api/question")
def api_question():
    """Return a new question as JSON."""
    age_group = session.get("age_group", 1)
    sub_difficulty = session.get("sub_difficulty", 1)
    q = _generate_question(age_group, sub_difficulty)
    # Store answer server-side so it can't be cheated
    session["current_answer"] = q["answer"]
    return jsonify(
        {
            "type": q["type"],
            "visual_html": q["visual_html"],
            "question_text": q["question_text"],
            "expression": q["expression"],
            "choices": q.get("choices", []),
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
        # Points scale with age group and sub-difficulty
        age_group = session.get("age_group", 1)
        sub_difficulty = session.get("sub_difficulty", 1)
        points = ((age_group - 1) * 3 + sub_difficulty) * 5
        score += points
        message = random.choice(
            [
                f"🎉 Awesome! +{points} points!",
                f"⭐ Brilliant! +{points} points!",
                f"🌟 Super! +{points} points!",
                f"🏆 Amazing! +{points} points!",
                f"✨ Fantastic! +{points} points!",
                f"🎯 Perfect! +{points} points!",
            ]
        )
    else:
        wrong += 1
        message = f"😕 Oops! The answer was {correct_answer}."

    session["score"] = score
    session["wrong"] = wrong
    session["total"] = total

    game_over = wrong >= max_wrong

    if game_over:
        # Save score to leaderboard
        player_name = session.get("player_name")
        if player_name:
            _save_game_result(player_name, score, total, total - wrong)

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
    top10 = sorted(
        data["leaderboard"], key=lambda x: x["score"], reverse=True
    )[:10]
    return render_template(
        "gameover.html",
        player_name=session["player_name"],
        avatar=session.get("avatar", "🧑"),
        score=score,
        total=total,
        correct=correct,
        wrong=wrong,
        leaderboard=top10,
        age_group=session.get("age_group", 1),
        sub_difficulty=session.get("sub_difficulty", 1),
    )


@app.route("/leaderboard")
def leaderboard():
    """Full leaderboard page."""
    data = _load_data()
    top10 = sorted(
        data["leaderboard"], key=lambda x: x["score"], reverse=True
    )[:10]
    return render_template("leaderboard.html", leaderboard=top10)


@app.route("/logout")
def logout():
    """Log out and return to login screen."""
    session.clear()
    return redirect(url_for("index"))
