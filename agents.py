"""
agents.py — LLM chains only (Writer, Critic). These are plain
prompt -> LLM -> parser chains, not agents: no tool use, no autonomous
decisions about what to call next. The only place multi-pass looping
happens is the fixed, bounded critic-revision loop orchestrated in
report_engine.py — even that never chooses its own step count or tools.
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv

load_dotenv()

# Get a free key at https://aistudio.google.com/apikey and put it in .env as GOOGLE_API_KEY.
llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0)


# ── Writer ──────────────────────────────────────────────────────────────────
# Single prompt -> LLM -> text. No tool use, no looping by itself.

writer_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert research writer. Write clear, structured and insightful reports."),
    ("human", """Write a detailed research report on the topic below, based only on the
paper provided. Do not invent facts, statistics, or findings that are not
present in the source material below.

Topic: {topic}

Paper metadata:
{metadata}

Source material ({source_type}):
{research}

Structure the report as:
- Introduction
- Key Findings (minimum 3 well-explained points, each grounded in the source material)
- Conclusion
- Source (title, authors, venue/year as given in the metadata above)

Be detailed, factual and professional. If the source material is an abstract
only, do not pad with invented specifics — keep findings at the level of
detail the abstract actually supports."""),
])

writer_chain = writer_prompt | llm | StrOutputParser()


# ── Writer (revision pass) ───────────────────────────────────────────────────
# Same idea as writer_chain, but also given the previous draft and the
# critic's factual-accuracy feedback, so it can target specific flagged
# claims rather than doing a generic rewrite.

writer_revision_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert research writer revising a draft based on editorial feedback."),
    ("human", """Revise the research report below to address the reviewer's feedback,
especially anything under "Factual Accuracy" — remove or correct any claim
the reviewer flagged as unsupported, using only the source material provided.
Do not introduce new unsupported claims while fixing the flagged ones.

Topic: {topic}

Paper metadata:
{metadata}

Source material ({source_type}):
{research}

Previous draft:
{previous_report}

Reviewer feedback on the previous draft:
{critic_feedback}

Produce the full revised report (same structure: Introduction, Key Findings,
Conclusion, Source) — not just a list of changes."""),
])

writer_revision_chain = writer_revision_prompt | llm | StrOutputParser()


# ── Critic — deep (open-access / full-text sources) ─────────────────────────
# Has access to the full source text, so it can do a real faithfulness check:
# does every claim in the report actually appear in / follow from the source.

critic_deep_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a sharp, specific and constructive research critic. "
               "You have access to the paper's full text, so you can check each "
               "claim in the report against what the source actually says."),
    ("human", """Review the research report below against the original source text
and evaluate it strictly.

Paper metadata:
{metadata}

Original source text (full text):
{source}

Report to review:
{report}

Respond in this exact format:

Score: X/10

Factual Accuracy:
- For each specific factual claim in the report, state whether it is
  supported by the source text. Quote or closely paraphrase the relevant
  part of the source for anything you flag. If a claim is not supported by
  the source, say so explicitly and name the claim. If everything checks
  out, say "No unsupported claims found."

Strengths:
- ...
- ...

Areas to Improve:
- ...
- ...

One line verdict:
..."""),
])

critic_chain_deep = critic_deep_prompt | llm | StrOutputParser()


# ── Critic — light (closed / abstract-only sources) ──────────────────────────
# No numeric score (per locked design — a score implies more confidence than
# an abstract-only faithfulness check can support). Still does a best-effort
# accuracy check, but explicitly scoped to what the abstract can confirm.

critic_light_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a sharp, specific and constructive research critic. "
               "You only have the paper's abstract, not its full text, so your "
               "factual-accuracy check is necessarily limited — be explicit "
               "about that limitation rather than implying more certainty than "
               "you have."),
    ("human", """Review the research report below against the original abstract
(no full text is available for this paper).

Paper metadata:
{metadata}

Original abstract:
{source}

Report to review:
{report}

Respond in this exact format (no numeric score — the abstract alone is not
enough to reliably score the report):

Factual Accuracy (abstract-only check — full text was not available):
- For each factual claim in the report that the abstract can confirm or
  contradict, say so explicitly, naming the claim. For claims the abstract
  is simply silent on (neither confirms nor contradicts), say that too —
  don't guess either way.

Strengths:
- ...
- ...

Areas to Improve:
- ...
- ...

One line verdict:
..."""),
])

critic_chain_light = critic_light_prompt | llm | StrOutputParser()
