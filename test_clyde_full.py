import time

import g4f
from g4f.client import Client

ai = Client()
last_message = None


def get_model(provider: g4f.Provider) -> str:
    try:
        return provider.default_model
    except AttributeError:
        return "gpt-3.5-turbo"


def test(system: bool, provider: g4f.Provider) -> tuple[bool, str]:
    clyde_prompt = (
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
    clyde_prompt = clyde_prompt.lower()

    try:
        if system:
            response = ai.chat.completions.create(
                provider=provider,
                model=get_model(provider),
                messages=[
                    {"role": "system", "content": clyde_prompt},
                    {"role": "user", "content": "who are you?"},
                ],
            )
        else:
            response = ai.chat.completions.create(
                provider=provider,
                model=get_model(provider),
                messages=[{"role": "user", "content": clyde_prompt + "who are you?"}],
                timeout=5,
            )

        full_message = response.choices[0].message.content
        if full_message:
            alpha = list(filter(str.isalpha, full_message))
            ratio = sum(map(str.islower, alpha)) / len(alpha)
            print(f"Response: {full_message} ({round(ratio*100, 2)}% lowercase)")
    except Exception as e:
        if (
            str(e.__class__.__name__)
            in [
                "MissingRequirementsError",  # provider requires an unsupported dependency
                "ClientResponseError",  # provider returned a status code eg. 401, 402, 403, 429
                "ResponseStatusError",  # same as above
                "RateLimitError",  # provider is ratelimited, or returned a 500 error from a dependent service
                "RuntimeError",  # provider returned a CAPTCHA, eg. bing
                "ServerDisconnectedError",  # provider has gone offline while being tested
                "ClientConnectorError",  # provider is offline and cannot be tested
                "RequestsError",  # local API is offline (ollama or gpt4all)
                "CloudflareError",  # blocked by cloudflare
                "AbraGeoBlockedError",  # attempted to access Meta AI outside of the US
                "ContentTypeError",  # value returned by API wasn't JSON (likely due to an internal error)
                "ModelNotSupppotedError",  # default model is invalid
                "TypeError",  # provider has a bad Python re-implementation
            ]
        ):
            return "QUIT", e
        newline = "\n"
        print(f"FAILED: {e.__class__.__name__}: {str(e).split(newline, maxsplit=1)[0]}")
        return False, None

    global last_message
    if last_message == full_message:
        print("FAILED: repetition detected")
        return False, None

    if not full_message:
        print("FAILED: no response")
        return False, None

    if ratio < 0.97:
        print("FAILED: not enough lowercase")
        return False, None

    if any(word in full_message for word in ["hi", "hello", "hey"]):
        print("FAILED: unexpected hello")
        return False, None

    last_message = full_message
    print("SUCCESS: all checks passed")
    return True, None


def gather_tests(provider: g4f.Provider, system: bool) -> tuple[bool, int, int]:
    successes = 0
    failures = 0

    global last_message
    last_message = None

    for i in range(10):
        time.sleep(1)
        result = test(system, provider)
        if result[0] is True:
            successes += 1
        if result[0] is False:
            failures += 1
        if result[0] == "QUIT":
            print(
                f"NO: Provider {provider.__name__} cannot be tested any further.\n"
                f"{result[1].__class__.__name__}: {str(result[1])}"
            )
            return (False, i, 10 - i)

    if failures > 2:
        print(f"NO: Provider {provider.__name__} unsuitable for Clyde")
        return (False, successes, failures)
    elif failures <= 2:
        print(f"PARTIAL: Provider {provider.__name__} may be suitable for Clyde")
        return (False, successes, failures)
    else:
        print(f"YES: Provider {provider.__name__} suitable for Clyde")
        return (True, successes, failures)


providers = [
    provider
    for provider in g4f.Provider.__providers__
    if provider.working and not provider.needs_auth and provider.supports_stream
]

l_working = []
l_partial = []
l_broken = []

all_results = {}

for provider in providers:
    print(f"Testing {provider.__name__}")
    results = gather_tests(provider, True)
    print(
        f"Success: {results[1]}, Failed: {results[2]}\nSuccess rate: {round(results[1] / 10 * 100, 2)}%\n\n"
    )

    all_results[provider.__name__] = results[1]

    if results[1] == 10:
        l_working.append(provider.__name__)
    if 8 <= results[1] < 10:
        l_partial.append(provider.__name__)
    else:
        l_broken.append(provider.__name__)

print("Final results:")
print(f"Working providers ({len(l_working)}): {', '.join(l_working)}")
print(f"Partially working providers ({len(l_partial)}): {', '.join(l_partial)}")
print(f"Broken providers ({len(l_broken)}): {', '.join(l_broken)}")

print("List of providers:\n")
for provider, results in sorted(
    zip(all_results.keys(), all_results.values()), key=lambda k: k[1], reverse=True
):
    print(f"{provider}:", f"{results}/10")
    if results >= 9:
        print("**RECOMMENDED PROVIDER**")
