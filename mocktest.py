import gradio as gr
import PyPDF2
import google.generativeai as genai
import re

# ✅ Configure Gemini API key (replace with your new key!)
genai.configure(api_key="AIzaSyBzAPn9uMGb5WxHnk6kgNzEyPz3bdaqmMU")

# ---------- UTILS ----------

def extract_resume_text(file):
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def generate_questions(resume_text, num_questions):
    # Improved prompt for real technical questions
    prompt = f"""
You are a strict technical interviewer for a software engineering role.

Based ONLY on the resume below, create {num_questions} challenging technical mock interview questions.
Focus on coding, algorithms, data structures, frameworks, and system design topics mentioned in the resume.
Avoid generic HR or behavioral questions.

Resume:
{resume_text}

Format:
1. [Question 1]
2. [Question 2]
...

Only output the questions.
"""
    model = genai.GenerativeModel('gemini-2.0-flash')
    response = model.generate_content(prompt)
    # Split questions by line and clean empty entries
    questions = [q.strip() for q in response.text.strip().split("\n") if q.strip()]
    return questions

def analyze_answer(answer):
    # Analyze answer for confidence, clarity, relevance
    prompt = f"""
You are a professional interviewer.

Evaluate the following answer on three aspects:
- Confidence (0-10)
- Clarity (0-10)
- Relevance (0-10)

Also, provide short feedback for each aspect.

Answer:
{answer}

Respond in this format:
Confidence: X/10
Clarity: Y/10
Relevance: Z/10
Feedback: [your comments]
"""
    model = genai.GenerativeModel('gemini-2.0-flash')
    response = model.generate_content(prompt)
    return response.text

# ---------- STATEFUL HANDLER ----------

class InterviewBot:
    def __init__(self):
        self.resume_text = ""
        self.questions = []
        self.current_question_index = 0
        self.feedbacks = []
        self.score_total = 0
        self.num_questions = 0

    def reset(self):
        self.resume_text = ""
        self.questions = []
        self.current_question_index = 0
        self.feedbacks = []
        self.score_total = 0
        self.num_questions = 0

    def set_resume(self, text):
        self.resume_text = text

    def set_questions(self, num_questions):
        self.num_questions = num_questions
        self.questions = generate_questions(self.resume_text, num_questions)
        self.current_question_index = 0
        self.feedbacks = []
        self.score_total = 0

    def get_next_question(self):
        if self.current_question_index < self.num_questions:
            return self.questions[self.current_question_index]
        return "✅ No more questions. Click 'Finish & Show Final Score'."

    def evaluate_answer(self, answer):
        feedback = analyze_answer(answer)
        self.feedbacks.append(feedback)

        # Extract scores from feedback text
        score_sum = 0
        for metric in ["Confidence", "Clarity", "Relevance"]:
            match = re.search(fr"{metric}:\s*(\d{{1,2}})/10", feedback, re.IGNORECASE)
            if match:
                score_sum += int(match.group(1))

        self.score_total += score_sum
        self.current_question_index += 1

        return feedback

    def final_score(self):
        max_score = self.num_questions * 30
        return f"✅ Final Score: {self.score_total}/{max_score}"

# ---------- INIT BOT ----------

bot = InterviewBot()

# ---------- GRADIO UI ----------

with gr.Blocks() as demo:
    gr.Markdown("## 🤖 **AI Interviewer Bot** — Technical Resume-based Mock Interview")

    with gr.Tab("Step 1: Add Resume"):
        with gr.Row():
            resume_file = gr.File(label="Upload Resume (PDF)")
            resume_manual = gr.Textbox(label="Or Paste Resume", lines=10, placeholder="Paste your full resume here...")

        upload_btn = gr.Button("Use Uploaded Resume")
        paste_btn = gr.Button("Use Manual Resume")
        resume_display = gr.Textbox(label="Parsed Resume Content", lines=10, interactive=False)

    with gr.Tab("Step 2: Select Questions"):
        num_questions = gr.Slider(1, 10, value=5, step=1, label="Number of Technical Questions")
        start_btn = gr.Button("Generate Questions and Start Interview")

    with gr.Tab("Step 3: Interview"):
        current_question = gr.Textbox(label="Question", interactive=False)
        user_answer = gr.Textbox(label="Your Answer", lines=3)
        submit_answer = gr.Button("Submit Answer")
        feedback = gr.Textbox(label="AI Feedback", lines=6, interactive=False)
        next_question = gr.Button("Next Question")

    with gr.Tab("Step 4: Score"):
        show_score = gr.Button("Finish & Show Final Score")
        score_display = gr.Textbox(label="Result", lines=2, interactive=False)

    # ---------- LOGIC ----------

    def handle_uploaded_resume(file):
        text = extract_resume_text(file.name)
        bot.reset()
        bot.set_resume(text)
        return text

    def handle_pasted_resume(text):
        bot.reset()
        bot.set_resume(text)
        return text

    def start_interview(n):
        bot.set_questions(n)
        return bot.get_next_question()

    def handle_answer(answer):
        feedback = bot.evaluate_answer(answer)
        return feedback

    def handle_next():
        return bot.get_next_question()

    def show_final_score():
        return bot.final_score()

    # ---------- BIND EVENTS ----------

    upload_btn.click(fn=handle_uploaded_resume, inputs=resume_file, outputs=resume_display)
    paste_btn.click(fn=handle_pasted_resume, inputs=resume_manual, outputs=resume_display)
    start_btn.click(fn=start_interview, inputs=num_questions, outputs=current_question)
    submit_answer.click(fn=handle_answer, inputs=user_answer, outputs=feedback)
    next_question.click(fn=handle_next, outputs=current_question)
    show_score.click(fn=show_final_score, outputs=score_display)

# ---------- RUN ----------

demo.launch()
