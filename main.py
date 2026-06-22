from openai import OpenAI

client = OpenAI()

while True:
    soru = input("Sor: ")

    cevap = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Sen mühendislik hesapları yapan bir asistansın"},
            {"role": "user", "content": soru}
        ]
    )

    print("Cevap:", cevap.choices[0].message.content)
