from flask import Flask, render_template, request, redirect, url_for, send_file
import sqlite3
import re
import os
from collections import Counter
from io import BytesIO

from dotenv import load_dotenv
from google import genai

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from xml.sax.saxutils import escape


app = Flask(__name__)
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
client = None
if api_key:
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        print(f"Warning: Could not initialize Gemini client: {e}")


# ---------------------------------------------------------
# DATABASE FUNCTIONS
# ---------------------------------------------------------

def save_note(study_material, summary, key_points):
    connection = sqlite3.connect("notes.db")
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO notes (
            study_material,
            summary,
            key_points,
            revision_questions
        )
        VALUES (?, ?, ?, ?)
    """, (
        study_material,
        summary,
        "\n".join(key_points),
        ""
    ))

    connection.commit()
    connection.close()


def get_saved_notes():
    connection = sqlite3.connect("notes.db")
    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()

    cursor.execute("""
        SELECT * FROM notes
        ORDER BY id DESC
    """)

    notes = cursor.fetchall()

    connection.close()

    return notes


# ---------------------------------------------------------
# TEXT PROCESSING
# ---------------------------------------------------------

def split_sentences(text):
    """
    Split study material into sentences.
    """

    sentences = re.split(r'(?<=[.!?])\s+', text.strip())

    sentences = [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]

    return sentences


def clean_words(sentence):
    """
    Extract useful words from a sentence.
    """

    stop_words = {
        "the", "is", "are", "was", "were",
        "a", "an", "and", "or", "but",
        "of", "to", "in", "on", "for",
        "with", "by", "from", "as",
        "at", "that", "this", "these",
        "those", "it", "its", "be",
        "has", "have", "had", "can",
        "will", "would", "could",
        "should", "their", "there",
        "they", "them", "we", "our",
        "you", "your", "which",
        "into", "also", "than",
        "about", "over", "after",
        "before", "during", "through",
        "more", "most", "very"
    }

    words = re.findall(r'\b[a-zA-Z]{3,}\b', sentence.lower())

    useful_words = [
        word for word in words
        if word not in stop_words
    ]

    return useful_words


# ---------------------------------------------------------
# SUMMARY GENERATION
# ---------------------------------------------------------

# ---------------------------------------------------------
# GEMINI AI SUMMARIZATION
# ---------------------------------------------------------

def ai_summarize_text(text):
    """
    Generate an AI-based summary and key points using Gemini.
    """

    prompt = f"""
You are an academic study-notes assistant.

Analyze the following study material and create:

1. A concise and clear summary.
2. Important key points for revision.

Rules:
- Use only information provided in the study material.
- Do not invent or add facts.
- Keep only the most important concepts, definitions, facts, names, dates, formulas, and information.
- Remove examples, repetition, explanations, and unnecessary details unless they are essential.
- Make the summary very concise: preferably 1–2 short sentences.
- Do not rewrite the study material.
- Generate 3–5 key points maximum.
- Each key point must be short and focused on one important idea.
- Do not repeat the same information in multiple key points.
- Key points should be useful for quick exam revision.
- The output should be concise and easy for a college student to revise.

Return the answer exactly in this format:

SUMMARY:
[Write the concise summary here]

KEY POINTS:
- [Key point 1]
- [Key point 2]
- [Key point 3]

STUDY MATERIAL:
{text}
"""

    if client:
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )

            result = response.text.strip()

            # Separate summary and key points
            if "KEY POINTS:" in result:
                summary_part, key_points_part = result.split(
                    "KEY POINTS:", 1
                )

                summary = summary_part.replace(
                    "SUMMARY:", ""
                ).strip()

                key_points = []

                for line in key_points_part.splitlines():
                    line = line.strip()

                    if line.startswith("-"):
                        line = line[1:].strip()

                    if line:
                        key_points.append(line)

                return summary, key_points

            if result:
                return result, create_key_points(text)
        except Exception as e:
            print(f"Gemini API error: {e}. Falling back to local NLP summarization.")

    # Fallback to local built-in summarizer
    return summarize_text(text), create_key_points(text)

def summarize_text(text):
    """
    Generate a concise extractive summary.
    """

    sentences = split_sentences(text)

    if not sentences:
        return ""

    if len(sentences) <= 2:
        return " ".join(sentences)

    word_frequency = Counter()

    for sentence in sentences:
        word_frequency.update(
            clean_words(sentence)
        )

    scored_sentences = []

    for index, sentence in enumerate(sentences):

        words = clean_words(sentence)

        if not words:
            continue

        score = sum(
            word_frequency[word]
            for word in words
        ) / len(words)

        # Give the beginning a small importance boost.
        if index == 0:
            score += 2

        if index == 1:
            score += 1

        scored_sentences.append(
            (score, index, sentence)
        )

    # Select only 2 important sentences.
    number_of_sentences = min(
        2,
        len(scored_sentences)
    )

    selected = sorted(
        scored_sentences,
        reverse=True
    )[:number_of_sentences]

    # Restore original order.
    selected = sorted(
        selected,
        key=lambda item: item[1]
    )

    return " ".join(
        item[2]
        for item in selected
    )


def create_key_points(text):
    """
    Create meaningful revision points that are different
    from the generated summary.
    """

    sentences = split_sentences(text)

    if not sentences:
        return []

    # Calculate word importance.
    word_frequency = Counter()

    for sentence in sentences:
        word_frequency.update(
            clean_words(sentence)
        )

    # Generate the summary first.
    summary = summarize_text(text)

    # Words used in the summary.
    summary_words = set(
        clean_words(summary)
    )

    scored_sentences = []

    for index, sentence in enumerate(sentences):

        words = clean_words(sentence)

        if not words:
            continue

        score = sum(
            word_frequency[word]
            for word in words
        ) / len(words)

        # Measure how much this sentence overlaps
        # with the summary.
        sentence_words = set(words)

        if sentence_words:
            overlap = len(
                sentence_words & summary_words
            ) / len(sentence_words)
        else:
            overlap = 0

        # Strongly reduce sentences that repeat
        # the information already present in summary.
        score = score * (1 - overlap)

        scored_sentences.append(
            (score, index, sentence)
        )

    # Rank by adjusted importance.
    ranked = sorted(
        scored_sentences,
        key=lambda item: item[0],
        reverse=True
    )

    key_points = []

    for score, index, sentence in ranked:

        words = sentence.split()
        word_count = len(words)

        # Ignore very short sentences.
        if word_count < 7:
            continue

        # Ignore excessively long sentences.
        if word_count > 45:
            continue

        # Remove accidental trailing words such as "see".
        sentence = re.sub(
            r'\s+see\s*\.?$',
            '.',
            sentence,
            flags=re.IGNORECASE
        ).strip()

        # Avoid duplicate points.
        if sentence in key_points:
            continue

        # Ignore sentences with very high summary overlap.
        sentence_words = set(
            clean_words(sentence)
        )

        if summary_words and sentence_words:

            overlap = len(
                sentence_words & summary_words
            ) / len(sentence_words)

            if overlap > 0.65:
                continue

        key_points.append(sentence)

        if len(key_points) == 4:
            break

    # Return points in their original order.
    key_points.sort(
        key=lambda point: sentences.index(
            point
        ) if point in sentences else 999
    )

    return key_points
# ---------------------------------------------------------
# HOME PAGE
# ---------------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html")


# ---------------------------------------------------------
# SUMMARIZE
# ---------------------------------------------------------

@app.route("/summarize", methods=["POST"])
def summarize():

    study_material = request.form.get(
        "study_material",
        ""
    ).strip()

    if not study_material:
        return render_template(
            "index.html",
            message="Please enter study material first."
        )
    
    summary, key_points = ai_summarize_text(study_material)

    return render_template(
        "index.html",
        study_material=study_material,
        summary=summary,
        key_points=key_points
    )


# ---------------------------------------------------------
# SAVE NOTE
# ---------------------------------------------------------

@app.route("/save", methods=["POST"])
def save():

    study_material = request.form.get(
        "study_material",
        ""
    ).strip()

    if not study_material:
        return redirect(url_for("home"))

    summary, key_points = ai_summarize_text(
        study_material
)

    save_note(
        study_material,
        summary,
        key_points
    )

    return render_template(
        "index.html",
        study_material=study_material,
        summary=summary,
        key_points=key_points,
        message="Note saved successfully!"
    )


# ---------------------------------------------------------
# VIEW SAVED NOTES
# ---------------------------------------------------------

@app.route("/notes")
def view_notes():

    search = request.args.get(
        "search",
        ""
    ).strip()

    if search:

        connection = sqlite3.connect(
            "notes.db"
        )

        connection.row_factory = sqlite3.Row

        cursor = connection.cursor()

        cursor.execute("""
            SELECT * FROM notes
            WHERE study_material LIKE ?
               OR summary LIKE ?
               OR key_points LIKE ?
            ORDER BY id DESC
        """, (
            "%" + search + "%",
            "%" + search + "%",
            "%" + search + "%"
        ))

        notes = cursor.fetchall()

        connection.close()

    else:
        notes = get_saved_notes()

    return render_template(
        "notes.html",
        notes=notes,
        search=search
    )


# ---------------------------------------------------------
# EDIT NOTE
# ---------------------------------------------------------

@app.route(
    "/edit/<int:note_id>",
    methods=["GET", "POST"]
)
def edit_note(note_id):

    connection = sqlite3.connect(
        "notes.db"
    )

    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()

    if request.method == "POST":

        study_material = request.form.get(
            "study_material",
            ""
        ).strip()

        summary, key_points = ai_summarize_text(
          study_material
)
        cursor.execute("""
            UPDATE notes
            SET study_material = ?,
                summary = ?,
                key_points = ?,
                revision_questions = ?
            WHERE id = ?
        """, (
            study_material,
            summary,
            "\n".join(key_points),
            "",
            note_id
        ))

        connection.commit()
        connection.close()

        return redirect(
            url_for("view_notes")
        )

    cursor.execute("""
        SELECT * FROM notes
        WHERE id = ?
    """, (note_id,))

    note = cursor.fetchone()

    connection.close()

    if note is None:
        return "Note not found."

    return render_template(
        "edit.html",
        note=note
    )


# ---------------------------------------------------------
# DELETE NOTE
# ---------------------------------------------------------
@app.route(
    "/delete/<int:note_id>",
    methods=["GET", "POST"]
)

def delete_note(note_id):

    connection = sqlite3.connect(
        "notes.db"
    )

    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM notes
        WHERE id = ?
    """, (note_id,))

    connection.commit()
    connection.close()

    return redirect(
        url_for("view_notes")
    )

# ---------------------------------------------------------
# EXPORT NOTE AS PDF
# ---------------------------------------------------------

@app.route(
    "/export/<int:note_id>"
)
def export_note(note_id):

    connection = sqlite3.connect(
        "notes.db"
    )

    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()

    cursor.execute("""
        SELECT * FROM notes
        WHERE id = ?
    """, (note_id,))

    note = cursor.fetchone()

    connection.close()

    if note is None:
        return "Note not found."

    pdf_buffer = BytesIO()

    document = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4
    )

    styles = getSampleStyleSheet()

    title_style = styles["Title"]
    heading_style = styles["Heading2"]
    normal_style = styles["BodyText"]

    story = []

    story.append(
        Paragraph(
            "Smart Notes Summarizer",
            title_style
        )
    )

    story.append(
        Spacer(1, 15)
    )

    story.append(
        Paragraph(
            "Study Material",
            heading_style
        )
    )

    story.append(
        Paragraph(
            escape(
                note["study_material"]
            ).replace("\n", "<br/>"),
            normal_style
        )
    )

    story.append(
        Spacer(1, 15)
    )

    story.append(
        Paragraph(
            "Summary",
            heading_style
        )
    )

    story.append(
        Paragraph(
            escape(
                note["summary"]
            ).replace("\n", "<br/>"),
            normal_style
        )
    )

    story.append(
        Spacer(1, 15)
    )

    story.append(
        Paragraph(
            "Key Points",
            heading_style
        )
    )

    key_points = note["key_points"].split(
        "\n"
    )

    for point in key_points:

        if point.strip():

            story.append(
                Paragraph(
                    "• " + escape(point),
                    normal_style
                )
            )

            story.append(
                Spacer(1, 5)
            )

    document.build(story)

    pdf_buffer.seek(0)

    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name="smart_notes.pdf",
        mimetype="application/pdf"
    )


# ---------------------------------------------------------
# RUN APPLICATION
# ---------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)