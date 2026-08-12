"""Exercise 2: run a small open-source model locally (no API key needed)."""

from transformers import pipeline

MODEL = "bigscience/bloomz-560m"
CONTEXT_TOKEN_BUDGET = 1400  # bloomz-560m's seq_length is 2048; leave room for prompt/question/output

_generator = None


def _get_generator():
    global _generator
    if _generator is None:
        _generator = pipeline("text-generation", model=MODEL)
    return _generator


def _truncate_to_budget(document: str) -> str:
    tokenizer = _get_generator().tokenizer
    ids = tokenizer(document)["input_ids"]
    if len(ids) <= CONTEXT_TOKEN_BUDGET:
        return document
    return tokenizer.decode(ids[:CONTEXT_TOKEN_BUDGET], skip_special_tokens=True)


def answer_question(document: str, question: str, temperature: float, system_prompt: str) -> str:
    """Grounded QA using the local model. Document is truncated to fit the context window."""
    generator = _get_generator()
    truncated_document = _truncate_to_budget(document)
    prompt = f"{system_prompt}\n\nמסמך:\n{truncated_document}\n\nשאלה: {question}\nתשובה:"

    if temperature == 0:
        result = generator(prompt, max_new_tokens=120, min_new_tokens=10, do_sample=False)
    else:
        result = generator(prompt, max_new_tokens=120, min_new_tokens=10, do_sample=True, temperature=temperature)

    generated = result[0]["generated_text"]
    return generated[len(prompt):].strip()


def main() -> None:
    prompt = "Give me 3 tips for reducing taxable income as a self-employed person."
    result = _get_generator()(prompt, max_new_tokens=100, min_new_tokens=20, do_sample=True)
    print(result[0]["generated_text"])


if __name__ == "__main__":
    main()
