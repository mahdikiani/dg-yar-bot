from enum import Enum


class AIEngines(str, Enum):
    gpt_4o = "gpt-4o"
    gpt_4o_mini = "gpt-4o-mini"
    gpt_4_turbo = "gpt-4-turbo"
    gpt_4 = "gpt-4"
    gpt35turbo = "gpt-3.5-turbo"
    claud3opus = "claud-3-opus"
    claud3sonnet = "claud-3-sonnet"
    claud3haiku = "claud-3-haiku"

    @classmethod
    def default(cls):
        return cls.gpt_4o

    @property
    def metis_bot_id(self):
        return {
            AIEngines.gpt_4o: "c5a435e6-335b-419a-8386-41247bb6a359",
        }[self]

    @property
    def tapsage_bot_id(self):
        return {
            AIEngines.gpt_4o: "55d1e911-67f1-493c-b4ff-bbafcca0e26b",
            AIEngines.gpt_4o_mini: "b6eff700-4cde-4407-93e6-0a93de7db61d",
            AIEngines.gpt_4_turbo: "3e0640f3-286e-4c4d-abea-0993d522771f",
            AIEngines.gpt_4: "288f04e2-728d-4be4-af0b-83ae1b97b87a",
            AIEngines.gpt35turbo: "03d99ad7-e344-4b0c-bbf5-46609f47d937",
            AIEngines.claud3opus: "0f87bb21-2357-49a4-a80d-d2f944b89671",
            AIEngines.claud3sonnet: "f9402e09-18b7-49e9-b08b-ad8bd8836511",
            AIEngines.claud3haiku: "2db268fe-914c-469e-b597-9ed46dc0f0f3",
        }[self]

    @classmethod
    def thumbnail_url(cls, engine: str):
        engine = AIEngines(engine)
        return {
            AIEngines.gpt_4o: "https://upload.wikimedia.org/wikipedia/commons/thumb/0/04/ChatGPT_logo.svg/512px-ChatGPT_logo.svg.png",
            AIEngines.gpt_4_turbo: "https://upload.wikimedia.org/wikipedia/commons/thumb/0/04/ChatGPT_logo.svg/512px-ChatGPT_logo.svg.png",
            AIEngines.gpt_4: "https://upload.wikimedia.org/wikipedia/commons/thumb/0/04/ChatGPT_logo.svg/512px-ChatGPT_logo.svg.png",
            AIEngines.gpt35turbo: "https://upload.wikimedia.org/wikipedia/commons/thumb/0/04/ChatGPT_logo.svg/512px-ChatGPT_logo.svg.png",
            AIEngines.claud3opus: "https://upload.wikimedia.org/wikipedia/commons/thumb/0/04/ChatGPT_logo.svg/512px-ChatGPT_logo.svg.png",
            AIEngines.claud3sonnet: "https://upload.wikimedia.org/wikipedia/commons/thumb/0/04/ChatGPT_logo.svg/512px-ChatGPT_logo.svg.png",
            AIEngines.claud3haiku: "https://upload.wikimedia.org/wikipedia/commons/thumb/0/04/ChatGPT_logo.svg/512px-ChatGPT_logo.svg.png",
        }[engine]

    @property
    def price(self):
        return {
            AIEngines.gpt_4o: 0.007,
            AIEngines.gpt_4_turbo: 0.007,
            AIEngines.gpt_4: 0.007,
            AIEngines.gpt35turbo: 0.007,
            AIEngines.claud3opus: 0.007,
            AIEngines.claud3sonnet: 0.007,
            AIEngines.claud3haiku: 0.007,
        }[self]
