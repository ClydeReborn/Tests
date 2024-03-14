import concurrent.futures

import g4f
from g4f.client import Client


def get_model(provider: g4f.Provider) -> str:
    try:
        return provider.default_model
    except AttributeError:
        return "gpt-3.5-turbo"


# gather all providers and values
_ = ["BaseProvider", "AsyncProvider", "AsyncGeneratorProvider", "RetryProvider"]
fails = []
fails_system = []
successes = []
successes_system = []
system_prompt = (
    "You are named Clyde and are currently chatting in a Discord server. "
    "You are friendly, warm and farcical. "
    "You must always be extremely concise. "
    "If the user is chatting casually, your responses must be less than 1 sentence, "
    "sometimes just a word or two. "
    "If the user needs help, disregard the length restriction, "
    "answer technical or knowledge-based questions with useful details and reasoning. "
    "If insulted, respond with a similar insult. "
    "Communicate responses in lowercase without punctuation, "
    "similar to the style used in chat rooms. "
    "Use unicode emoji rarely. "
    "Do not refer to yourself as a bot, AI Assistant, or any equivalent term. "
)
ai = Client()


# test system-less
def test_provider(provider):
    try:
        provider = g4f.Provider.ProviderUtils.convert[provider]
        if provider.working and not provider.needs_auth:
            print(f"Testing {provider.__name__} without a system prompt")
            response = ai.chat.completions.create(
                model=get_model(provider),
                messages=[{"role": "user", "content": system_prompt + "who are you?"}],
                provider=provider,
            )
            completion = response.choices[0].message.content
            if completion == "":
                raise RuntimeError("Empty response")

            return completion, provider.__name__
    except Exception:
        fails.append(f"ERROR: {provider.__name__} isn't working.")
    return None


# test with a system prompt
def system_test(provider):
    try:
        provider = g4f.Provider.ProviderUtils.convert[provider]
        if provider.working and not provider.needs_auth:
            print(f"Testing {provider.__name__} with a system prompt")
            response = ai.chat.completions.create(
                model=get_model(provider),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "who are you?"},
                ],
                provider=provider,
            )
            completion = response.choices[0].message.content
            if completion == "":
                raise RuntimeError("Empty response")

            return completion, provider.__name__
    except Exception:
        fails_system.append(
            f"ERROR: {provider.__name__} isn't working with system requests."
        )
    return None


# gather up all successful responses
with concurrent.futures.ThreadPoolExecutor() as executor:
    futures = [
        executor.submit(test_provider, provider)
        for provider in g4f.Provider.__all__
        if provider not in _
    ]

    futures_system = [
        executor.submit(system_test, provider)
        for provider in g4f.Provider.__all__
        if provider not in _
    ]

    for future in concurrent.futures.as_completed(futures):
        if result := future.result():
            successes.append(f"SUCCESS: {result[1]} is working: {result[0]}")

    for future in concurrent.futures.as_completed(futures_system):
        if result := future.result():
            successes_system.append(
                f"SUCCESS: {result[1]} accepted the system request: {result[0]}"
            )

# print the results
print("\n\n")
print(f"Working providers: {len(successes) + len(successes_system)}")
print(f"Broken providers: {len(fails) + len(fails_system)}")
print("\n\nDetails:\n")
print("\n".join(successes))
print("\n".join(successes_system))
print("\n".join(fails))
print("\n".join(fails_system))
