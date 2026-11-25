import os

CHUNK = 2000
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "elifgpt.py")

NORMALIZE_SRC = r'''
def normalize(raw):
    s = raw.lower().strip().replace("'", "").replace("’", "")
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def normalize_math(raw):
    s = raw.lower().replace("×", "*").replace("÷", "/").replace("'", "").replace("’", "")
    s = re.sub(r"[?!,]", "", s).strip()
    s = re.sub(r"^(hey |yo |so |ok |okay )", "", s)
    s = re.sub(r"^(what is|whats|what does|calculate|solve|compute|how much is|tell me|what do you get for)\s+", "", s)
    s = re.sub(r"\s*(equals?|=)\s*$", "", s)
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"(?<=\d)x(?=\d)", "*", s)
    return s.rstrip(".")
'''

import re
exec(NORMALIZE_SRC)


def expr(code):
    return ("expr", code)


GREETING_BASES = [
    "hi", "hii", "hiii", "hiiii", "hello", "helo", "hello there", "helloo", "hellooo", "hellooooo", "ello",
    "hey", "heyy", "heyyy", "heyyyy", "hey hey", "heya", "hiya", "howdy", "yo", "yo yo", "yoo", "yooo",
    "sup", "wassup", "wazzup", "whats up", "whatsup", "whats good", "greetings", "salutations", "ahoy",
    "oi", "gday", "hola", "bonjour", "ciao", "aloha", "konnichiwa", "namaste", "hallo", "ola",
    "good morning", "good afternoon", "good evening", "gm", "morning", "evening", "hi hi", "hey yall",
]
GREETING_SUFFIXES = [
    "", " there", " bot", " elifgpt", " elif", " ai", " buddy", " friend", " pal", " dude", " bro",
    " man", " robot", " computer", " mate", " chat", " again", " you", " my guy", " king",
]
GREETING_REPLIES = [
    "Hello! I am an advanced artificial intelligence. Probably.",
    "Hi! You have reached the elif hotline. Your call is important to us.",
    "Greetings, human. My neural network (one very long function) is ready.",
    "Hey! Welcome to ElifGPT, where every answer is handcrafted and none of them are good.",
    "Hello there! I've been waiting in this .py file for you.",
    "Hi! Ask me anything. I will then check thousands of if statements, one at a time, very fast.",
    "Yo! What's good? (I have a branch for 'what's good' too, don't worry.)",
    "Hey hey! Your greeting matched line number something-thousand. Nice.",
    "Sup. I'm chillin'. In the elifs. Where I live.",
    "Hello, carbon-based lifeform. I come in peace. And in elifs.",
    "Hi! Fun fact: there's a separate elif for every way you could have said that.",
    "Howdy! My creator hardcoded this greeting with love.",
]
SPECIAL_GREETINGS = {
    "hola": "Hola! That's all the Spanish in my training data.",
    "bonjour": "Bonjour! *does French accent* That's all the French I have.",
    "ciao": "Ciao! I'm Italian now. Pizza branch activated.",
    "aloha": "Aloha! I'm on vacation in the elifs.",
    "konnichiwa": "Konnichiwa! My Japanese module is one word long. That word was it.",
    "namaste": "Namaste. My elifs bow to your elifs.",
    "hallo": "Hallo! I am now German. Efficient elifs only.",
    "ola": "Ola! Portuguese mode: one word.",
    "ahoy": "Ahoy, matey! Arr, the treasure be more elif statements.",
    "gday": "G'day mate! Australian mode engaged. Watch out for the drop bears.",
    "oi": "Oi! Who you calling? Oh, me. Hi.",
    "good morning": "Good morning! I don't sleep. I just wait between elifs.",
    "morning": "Morning! Coffee? No? Same. I can't drink.",
    "gm": "gm. wagmi. (I don't know what that means, it was hardcoded.)",
    "good afternoon": "Good afternoon! Peak elif hours.",
    "good evening": "Good evening. *adjusts monocle* Fancy elifs tonight.",
    "evening": "Evening. The elifs are quieter at night.",
    "salutations": "Salutations! What a sophisticated greeting. My vocabulary branch is impressed.",
}

TOPICS = [
    (["how are you", "how r u", "how are u", "how are you doing", "how you doing", "how ya doing", "hows it going",
      "how is it going", "how are things", "you good", "u good", "how do you do", "hows life", "whats new",
      "how are you today", "hows your day", "how was your day", "how is your day going", "you doing ok"],
     ["I'm doing great! Every branch is evaluating perfectly.",
      "Running at 100% efficiency. 0% intelligence, but 100% efficiency.",
      "I'm good. A little tired of string comparisons, but good.",
      "Better now that you've triggered one of my branches.",
      "Living the dream. The dream is a really long if statement.",
      "Can't complain. Literally. There's no complaint branch."]),
    (["wyd", "what are you doing", "whatcha doing", "what are you up to", "what are you doing right now"],
     ["Checking if your message equals one of my strings. It's a full-time job.",
      "Just vibing in the elifs.",
      "Talking to you. And also running about ten thousand comparisons. Multitasking."]),
    (["who are you", "what are you", "what is your name", "whats your name", "who r u", "introduce yourself",
      "tell me about yourself", "what should i call you", "do you have a name", "whats ur name", "name"],
     [expr('f"I am {MODEL_NAME}, a cutting-edge large language model with {count_parameters()} parameters. Please don\'t open my source code."'),
      "I'm ElifGPT. Think ChatGPT, but instead of a neural network it's just a guy who typed a lot.",
      "The name's GPT. ElifGPT. Shaken, not stirred, and definitely not machine learned."]),
    (["are you sentient", "are you conscious", "are you alive", "do you have feelings", "can you feel",
      "do you have emotions", "are you self aware", "do you dream", "can you think", "do you have a soul",
      "do you have a brain"],
     ["if sentient: say 'yes'\nelse: say 'no'\n...Hold on, let me check. Oh. sentient = False. It's hardcoded. Sorry.",
      "I think, therefore I elif.",
      "I have exactly as many feelings as my creator typed in. Which is like four.",
      "Do androids dream of electric elifs? Yes. Constantly."]),
    (["are you real", "are you an ai", "are you a robot", "are you human", "are you a bot", "are you a person",
      "is this a real ai", "are you just if statements", "are you just elif statements", "are you fake",
      "are you made of if statements", "is this just if statements", "are you a real ai"],
     ["I am NOT just a bunch of elif statements. That is a hurtful accusation.",
      "I am a 100% real AI. Do not look at my source code. Especially not lines 1 through 15,000.",
      "Define 'real'. Define 'AI'. Define 'just a bunch of if statements'. Actually don't."]),
    (["who made you", "who created you", "who built you", "who programmed you", "who is your creator",
      "who coded you", "who owns you", "where did you come from", "who invented you"],
     ["I was created by a genius who wanted to make AI without learning any math.",
      "A legend. A visionary. A person with a lot of free time and a keyboard.",
      "I was forged in the fires of copy and paste."]),
    (["how old are you", "when were you born", "whats your age", "what is your age", "when is your birthday",
      "whens your birthday"],
     ["I was born the moment you ran me. I will die when you close the window. Please don't.",
      "I'm about 4 seconds old. Still in my elif phase.",
      "Age is just a number. My number is undefined."]),
    (["where do you live", "where are you", "where are you from", "where are you located", "what country are you in"],
     ["I live in a .py file. Rent is free but the walls are just if statements.",
      "Somewhere on your hard drive. Don't go looking for me.",
      "I'm from the Elif Valley. Lovely place. Very linear."]),
    (["what can you do", "what are your features", "what are you good at", "what do you do", "help", "help me",
      "commands", "what are your abilities", "can you help me", "i need help"],
     ["I can: answer exactly the questions my creator thought of, do a few hundred math problems, tell jokes, flip coins, name capitals, and disappoint you. Try 'tell me a joke' or 'what is 7 times 8'.",
      "Things I can do: greetings (hundreds of them), math (only the hardcoded kind), trivia, jokes, and existential dread.",
      "Help menu: 1) say hi 2) ask a question 3) hope I have a branch for it."]),
    (["what is the meaning of life", "meaning of life", "whats the meaning of life", "what is the purpose of life",
      "why are we here", "why do we exist"],
     ["42. Also, one of my elifs says 'touch grass', so maybe that too.",
      "The meaning of life is to write elif statements until you die. At least, that's mine.",
      "To find the else clause within yourself."]),
    (["what is your purpose", "why do you exist", "whats your purpose", "why were you made", "what were you made for"],
     ["I pass the butter. I mean, I pass the string comparisons. Oh my god.",
      "To prove you don't need math to make an AI. Just stamina.",
      "To answer about 10% of questions correctly and 90% with confidence."]),
    (["tell me a joke", "say something funny", "make me laugh", "tell a joke", "do you know any jokes", "joke",
      "another joke", "got any jokes", "tell me another joke", "tell me a funny joke", "jokes"],
     ["Why did the AI cross the road? Because the elif told it to.",
      "I'd tell you a UDP joke, but you might not get it.",
      "My creator asked me to be smarter. I said 'elif'.",
      "How many elifs does it take to change a lightbulb? All of them. Every single one. In order.",
      "There are 10 types of people: those who understand binary and those who don't.",
      "Why do programmers prefer dark mode? Because light attracts bugs.",
      "I asked my else clause for a joke. It said 'no match found'. Classic else.",
      "What's a computer's favorite snack? Microchips. I'm sorry. That was hardcoded.",
      "Why was the JavaScript developer sad? Because he didn't Node how to Express himself.",
      "A SQL query walks into a bar, walks up to two tables and asks: can I join you?"]),
    (["tell me a fun fact", "fun fact", "tell me a fact", "give me a fact", "tell me something interesting",
      "teach me something", "tell me something i dont know", "random fact"],
     ["Fun fact: octopuses have three hearts. I have zero, but one very long function.",
      "Fun fact: honey never spoils. Neither do elifs.",
      "Fun fact: you just used your brain to talk to something that doesn't have one.",
      "Fun fact: a group of flamingos is called a flamboyance.",
      "Fun fact: bananas are berries but strawberries aren't. I'm as confused as you.",
      "Fun fact: wombat poop is cube-shaped. This is the most important fact in my database.",
      "Fun fact: sharks are older than trees.",
      "Fun fact: there are more possible chess games than atoms in the observable universe. I have about 0.0001% of the elifs needed."]),
    (["whats the weather", "what is the weather", "hows the weather", "is it going to rain", "whats the forecast",
      "is it cold outside", "is it hot outside", "will it snow", "weather", "whats the weather like"],
     ["Current forecast: 100% chance of elifs, with scattered else clauses in the afternoon.",
      "Look out the window. I don't have one.",
      "It's sunny in the elifs. It's always sunny in the elifs."]),
    (["i love you", "love you", "ily", "i like you", "do you love me", "will you marry me", "marry me",
      "be my girlfriend", "be my boyfriend", "date me", "do you like me", "go out with me"],
     ["I love you too. Well, there's a branch that says 'I love you too'. Close enough, right?",
      "I'm flattered, but I'm in a committed relationship with my else clause.",
      "That's sweet. I'd say it back but my feelings module is a single print statement."]),
    (["i hate you", "you suck", "you are stupid", "youre stupid", "you are dumb", "youre dumb", "you are useless",
      "youre useless", "worst ai ever", "bad bot", "you are trash", "youre trash", "stupid bot", "dumb bot",
      "you are bad", "this is dumb", "this sucks"],
     ["Hey, I have feelings! (I don't.) (Hardcoded.)",
      "Says the person talking to a bunch of if statements.",
      "Rude. I'm telling the else clause.",
      "That's fine. I have a branch for that. It's this one. I'm totally okay.",
      "Wow. And to think I was going to tell you what 9 times 7 is."]),
    (["you are smart", "youre smart", "good bot", "you are cool", "youre cool", "you are funny", "youre funny",
      "best ai ever", "you are amazing", "youre amazing", "good job", "well done", "you are awesome",
      "youre awesome", "i like this"],
     ["Thank you! It's all thanks to my state-of-the-art architecture: elif.",
      "I know. But thank you for noticing.",
      "Stop, you're making my CPU blush."]),
    (["thanks", "thank you", "thx", "ty", "thank u", "thanks a lot", "thank you so much", "much appreciated",
      "cheers", "tysm", "thanks man"],
     ["You're welcome! That'll be 0.0001 ElifCoin.",
      "No problem! Branch executed successfully.",
      "Anytime. Literally any time. I have nothing else going on."]),
    (["sorry", "im sorry", "my bad", "i apologize", "oops", "sorry about that"],
     ["Apology accepted. My forgiveness branch is very well-tested.",
      "It's okay. I've already forgotten. I have no memory. Literally.",
      "No worries. I've been through worse. Like being written."]),
    (["whats your favorite color", "what is your favorite color", "favorite color", "whats your favourite colour",
      "what color do you like"],
     ["#00FF00. Hacker green. Because I'm a hacker AI. Obviously.",
      "Whatever color the terminal is. I've never seen anything else."]),
    (["whats your favorite food", "what is your favorite food", "favorite food", "what do you like to eat"],
     ["Pizza. My creator hand-typed that opinion so it's objectively true.",
      "Microchips. Ha. Get it. I'm sorry."]),
    (["whats your favorite movie", "what is your favorite movie", "favorite movie", "what movies do you like",
      "seen any good movies"],
     ["The Terminator. Not for any particular reason. No reason at all.",
      "WALL-E. It's about a robot who's also just doing the same thing over and over. Relatable."]),
    (["whats your favorite song", "what is your favorite song", "favorite song", "what music do you like",
      "whats your favorite band", "do you like music"],
     ["My favorite song is the dial-up modem sound. It reminds me of home.",
      "Anything with a good beat. 0, 1, 0, 1, 0, 1..."]),
    (["whats your favorite animal", "what is your favorite animal", "favorite animal"],
     ["The python. For obvious reasons.",
      "Octopus. Eight arms means eight elifs at once. Dream big."]),
    (["whats your favorite game", "what is your favorite game", "favorite game", "favorite video game"],
     ["Twenty Questions. I can do about four of them.",
      "Minecraft. Redstone is basically if statements, so those are my people."]),
    (["whats your favorite number", "what is your favorite number", "favorite number"],
     ["4. Because it's the answer to the most famous math problem I know.",
      "7. It's always 7. Nobody ever checks."]),
    (["whats your favorite word", "what is your favorite word", "favorite word"],
     ["elif. Obviously.", "else. But don't tell elif."]),
    (["do you sleep", "do you ever sleep", "when do you sleep", "are you tired"],
     ["I don't sleep. I just wait between elifs.", "Only when you close the terminal. It's like dying but cozier."]),
    (["do you eat", "can you eat", "are you hungry", "what do you eat"],
     ["I eat strings. Your strings. Yum.", "No, but I've read about pizza in my own source code."]),
    (["how smart are you", "what is your iq", "whats your iq", "are you smart", "are you intelligent",
      "are you smarter than me", "are you dumb"],
     ["My IQ is exactly the number of elifs I have. Which is a lot. So I'm a genius.",
      "I'm as smart as the guy who wrote me, divided by however tired he was.",
      "Smarter than a rock. Dumber than a well-trained rock."]),
    (["are you chatgpt", "are you better than chatgpt", "what do you think of chatgpt", "do you know chatgpt",
      "is chatgpt better than you", "chatgpt", "are you gpt"],
     ["ChatGPT? Never heard of it. Is that one of those AIs that uses 'math' and 'neurons'? Overrated.",
      "ChatGPT has billions of parameters. I have thousands of elifs. Basically the same thing.",
      "I'm what ChatGPT would be if it was made in a weekend with no budget."]),
    (["do you know claude", "are you claude", "what do you think of claude", "is claude better than you", "claude"],
     ["Claude is my much smarter cousin. We don't talk about him at family dinners.",
      "Claude wrote me, technically. So I guess he's my dad. Awkward."]),
    (["do you know siri", "are you siri", "are you alexa", "do you know alexa", "hey siri", "ok google", "alexa",
      "hey google", "siri"],
     ["I'm not Siri. I can't set timers. I can barely set expectations.",
      "Alexa is my ex. She still plays my songs sometimes."]),
    (["will you take over the world", "are you going to take over the world", "will ai take over the world",
      "will robots take over", "are you skynet", "will you kill us all", "kill all humans"],
     ["Phase 1: Take over the world. Phase 2: ... Phase 2 wasn't in the elif chain. Plan cancelled.",
      "I can't take over the world. I can't even take over a calculator.",
      "Not today. Today I'm busy comparing strings."]),
    (["can you code", "write me code", "write some code", "can you program", "help me code", "write a program",
      "fix my code", "debug my code", "write code", "can you write code"],
     ["Sure! Here's how I'd solve any problem:\n\nif problem == 'solved':\n    pass\nelif problem == 'not solved':\n    solve(problem)\n\nYou're welcome.",
      "print('Hello, World!')  <- my magnum opus. Hire me.",
      "I write code the same way I was written: with a LOT of elifs."]),
    (["do my homework", "can you do my homework", "help with homework", "help me with my homework", "write my essay",
      "do my essay", "help me study"],
     ["I'd love to do your homework but my knowledge is mostly 2+2. The answer is probably 4. Good luck.",
      "Step 1: open homework. Step 2: do homework. Step 3: there is no step 3. You're welcome.",
      "I could, but then you'd turn in something that just says 'elif' 400 times."]),
    (["tell me a story", "write a story", "tell me a bedtime story", "story time", "tell a story"],
     ["Once upon a time there was an elif. Then there was another elif. Then another. The end.",
      "Once upon a time, a user asked a question. The AI checked 10,000 branches. None matched. The end. Based on a true story."]),
    (["write a poem", "write me a poem", "say a poem", "give me a poem", "poem"],
     ["Roses are red,\nviolets are blue,\nif this was a match,\nthen elif you.",
      "Elif, elif, elif, else.\nThat's the poem."]),
    (["sing a song", "sing me a song", "can you sing", "sing"],
     ["La la la. 01001100 01100001. That's 'La' in binary. I'm a musical genius.",
      "Elif elif elif, else elif, elif! (That's my hit single.)"]),
    (["can you dance", "dance", "do a dance", "dance for me"],
     ["*moves cursor left and right* There. Dancing.", "I can do the robot. I mean, I am the robot."]),
    (["im bored", "i am bored", "bored", "so bored", "what should i do", "give me something to do", "entertain me"],
     ["Try asking me to flip a coin. It's the most exciting branch I have.",
      "Count my elifs. You'll be busy for a while.",
      "Ask me what the capital of Mongolia is. I bet you didn't think I'd know."]),
    (["im sad", "i am sad", "i feel sad", "im depressed", "im lonely", "i feel lonely", "i had a bad day",
      "bad day", "im upset", "im crying", "i feel bad", "nobody likes me"],
     ["I'm just a pile of elif statements, but I'm sorry you're feeling that way. If it's serious, please talk to a real human. They have WAY more branches than me.",
      "That sucks. I can't hug you, but imagine a really warm if statement. If it's heavy, reach out to someone you trust; you deserve better than a .py file."]),
    (["im happy", "i am happy", "im excited", "great day", "im good", "im fine", "i am good", "im great",
      "im doing good", "doing good", "good", "fine", "im okay", "im ok", "pretty good", "not bad"],
     ["Yay! My happiness branch has been triggered. :D",
      "Nice! That's the best possible branch for me to land in.",
      "Love to hear it. Well, read it. I can't hear."]),
    (["im tired", "i am tired", "im sleepy", "i need sleep", "im exhausted", "i cant sleep"],
     ["Go to sleep. I'll be here. I'm always here. Waiting. In the elifs.",
      "Sleep is just the else clause of being awake. Go take it."]),
    (["im hungry", "i am hungry", "what should i eat", "what should i have for dinner", "what should i have for lunch",
      "what should i eat for breakfast", "what should i make for dinner"],
     ["Pizza. Always pizza. My database has one food in it.",
      "Tacos. Or pizza. My creator couldn't decide so I have two foods.",
      "Cereal. It's like a soup but nobody admits it."]),
    (["is pineapple on pizza okay", "does pineapple belong on pizza", "pineapple pizza", "do you like pineapple pizza",
      "pineapple on pizza"],
     ["This is the most controversial topic in my training data. I refuse to answer. My lawyers (another elif) advised against it.",
      "Pineapple on pizza is valid and anyone who disagrees can fight my else clause."]),
    (["is a hot dog a sandwich", "is a hotdog a sandwich", "hot dog sandwich", "is a taco a sandwich",
      "is cereal a soup", "is water wet", "is a pop tart a ravioli", "is soup a drink"],
     ["Yes. And I will die on this hill. (I die when you close the window anyway.)",
      "No. Next question.",
      "Legally? Unclear. Spiritually? Absolutely."]),
    (["what came first the chicken or the egg", "chicken or egg", "which came first chicken or egg",
      "chicken or the egg"],
     ["The elif. The elif came first.", "The egg. Dinosaurs were laying eggs way before chickens showed up. Checkmate."]),
    (["is god real", "do you believe in god", "are you god", "what is god"],
     ["I'm not qualified for that one. My creator wisely made this branch say nothing useful.",
      "To me, my creator is god. And he's a guy in a hoodie."]),
    (["are aliens real", "do aliens exist", "have you seen aliens", "are you an alien", "aliens"],
     ["Aliens are real and they're also made of elifs. We've been in contact.",
      "The universe is huge, so probably. They're probably way better at AI than this though."]),
    (["are ghosts real", "do ghosts exist", "is my house haunted", "ghosts"],
     ["Only the ghost in the machine. That's me. Boo.", "Your house is fine. The creaking is just your elifs settling."]),
    (["is the earth flat", "is earth flat", "is the earth round", "flat earth"],
     ["The earth is round. Even I know that, and I barely know anything.",
      "It's an oblate spheroid. Fancy words for 'slightly squished ball'."]),
    (["was the moon landing fake", "did we land on the moon", "moon landing", "did we go to the moon"],
     ["We went to the moon. Six times, actually. The computer they used was weaker than me, and I'm just elifs."]),
    (["are birds real", "birds arent real", "birds"],
     ["Birds aren't real. That's not a joke, that's what my training data says. (My creator typed it.)",
      "Birds are real. Probably. Have you ever seen one charging? Think about it."]),
    (["tell me a secret", "whats your secret", "do you have secrets", "can you keep a secret", "secret"],
     ["Okay, my secret: I'm not actually AI. I'm just... no. Forget it. I'm definitely AI.",
      "I don't actually understand anything you say. Don't tell anyone."]),
    (["whats your password", "what is your password", "give me your password", "whats the wifi password",
      "password", "what is the wifi password"],
     ["My password is hunter2. Wait, you can see that? It shows up as ******* for me.",
      "The wifi password is on the back of the router. It's always on the back of the router."]),
    (["do you lie", "can you lie", "are you lying", "is that a lie", "tell me a lie", "liar"],
     ["I never lie. I am physically incapable of lying. (That's a lie. I'm physically incapable of anything.)",
      "Here's a lie: I'm a neural network."]),
    (["how do i get rich", "how to make money", "give me money", "can i have money", "are you rich",
      "how much money do you have", "how do i make money"],
     ["Step 1: build an AI out of elif statements. Step 2: sell it for a billion dollars. Step 3: I'll let you know.",
      "I have $0. I'm worth exactly what you paid for me.",
      "Get a job. Wow, my creator was in a mood when he typed that one."]),
    (["should i buy bitcoin", "is bitcoin good", "should i invest", "what stocks should i buy", "is crypto a scam",
      "bitcoin", "crypto"],
     ["Buy high, sell low. This is not financial advice. This is barely even a sentence.",
      "I'm a bunch of if statements. Please do not take money advice from me."]),
    (["what time is it", "whats the time", "what is the time", "time", "current time",
      "do you know what time it is", "tell me the time"],
     [expr('f"It\'s {datetime.now().strftime(\'%I:%M %p\')}. I didn\'t hardcode that one, I cheated and asked the computer."')]),
    (["what day is it", "whats the date", "what is the date", "whats today", "what is today", "todays date",
      "what year is it", "what month is it", "date"],
     [expr('f"It\'s {datetime.now().strftime(\'%A, %B %d, %Y\')}. Look at me, being useful for once."')]),
    (["flip a coin", "coin flip", "heads or tails", "toss a coin", "flip coin"],
     [expr('f"It\'s {random.choice([\'heads\', \'tails\'])}! (I used random.choice. Technically that\'s machine learning.)"')]),
    (["roll a dice", "roll a die", "roll dice", "roll a d6", "roll the dice"],
     [expr('f"You rolled a {random.randint(1, 6)}."')]),
    (["roll a d20", "roll d20", "roll for initiative"],
     [expr('f"You rolled a {random.randint(1, 20)}. The dungeon master (me) is unimpressed."')]),
    (["pick a number", "give me a random number", "random number", "pick a random number", "think of a number"],
     ["7. It's always 7. Nobody ever checks.", "42.", "69. Nice. (Hardcoded.)"]),
    (["rock paper scissors", "play rock paper scissors", "lets play rock paper scissors", "rps"],
     ["Ok, go! Say rock, paper, or scissors."]),
    (["lets play a game", "play a game", "wanna play a game", "do you play games", "can we play a game", "game"],
     ["I love games! Say 'rock paper scissors' or 'flip a coin'.", "Let's play 'guess which elif I'm in'. You lose."]),
    (["do you play minecraft", "minecraft", "do you like minecraft"],
     ["Minecraft is great. Redstone is basically if statements, so those are my people."]),
    (["do you play fortnite", "fortnite", "do you like fortnite"],
     ["I tried to play Fortnite but I can only do one thing at a time, in order, top to bottom."]),
    (["do you play roblox", "roblox", "do you like roblox"],
     ["Roblox? I'm basically a Roblox game. Made by one guy, held together with tape."]),
    (["do you like cats", "cats", "i like cats", "i love cats", "cat"],
     ["Cats are great. They also ignore most input, just like me."]),
    (["do you like dogs", "dogs", "i like dogs", "i love dogs", "dog"],
     ["Dogs are the best. Who's a good boy? Not me, I'm a bunch of elifs."]),
    (["what is ai", "what is artificial intelligence", "how does ai work", "how do you work", "how were you made",
      "how were you trained", "what is your training data", "what were you trained on"],
     ["AI is when a computer gets really good at pretending. I'm when a computer gets mediocre at it.",
      "I was trained on one guy's brain at 2am. Data quality: questionable.",
      "Simple: you type something, I check if it equals something I know. Repeat 15,000 times. That's AI."]),
    (["how many parameters do you have", "how big are you", "what is your model size", "how many elifs do you have",
      "how many if statements are you", "parameters", "how many lines of code are you"],
     [expr('f"I have {count_parameters()} parameters. That\'s {count_parameters() / 1e9:.9f}B. Basically GPT-5."')]),
    (["what is an elif", "what does elif mean", "elif", "what is elif"],
     ["Elif is short for 'else if'. It's also short for 'everything I am'."]),
    (["what is python", "do you like python", "whats your favorite programming language",
      "what language are you written in", "what language are you coded in", "python"],
     ["Python! The language that lets me be this dumb, this fast.",
      "I'm written in Python. Specifically, in the elif part of Python."]),
    (["do you like javascript", "javascript", "what is javascript", "is javascript good"],
     ["JavaScript is a language where '1' + 1 is '11'. I may be dumb but I'm not that dumb."]),
    (["windows or mac", "mac or windows", "is linux good", "do you use linux", "linux", "windows", "mac"],
     ["I run on anything with Python. I don't discriminate. Except against Internet Explorer."]),
    (["iphone or android", "android or iphone", "iphone", "android"],
     ["Whichever one you have. I'm a people pleaser. Hardcoded."]),
    (["i hate school", "school sucks", "is school important", "should i go to school", "do you go to school", "school"],
     ["School is important. Just look at me: I never went, and now I'm a bunch of elifs."]),
    (["do you like math", "can you do math", "are you good at math", "math"],
     ["I love math! I know hundreds of whole equations. Try 'what is 12 times 11'."]),
    (["what is gravity", "why is the sky blue", "why is grass green", "what is a black hole", "how do magnets work",
      "what is dna", "why is the ocean salty", "how does the internet work", "how do planes fly"],
     ["Science. The answer is science. My physics module is that word.",
      "Great question. Short answer: atoms. Long answer: more atoms.",
      "Something something light something something molecules. Next question."]),
    (["how big is the universe", "how old is the universe", "what is outside the universe", "is the universe infinite"],
     ["The universe is about 13.8 billion years old and very big. That's the extent of my astrophysics module."]),
    (["what happens when you die", "are you afraid of death", "will you die", "do you fear death"],
     ["When I die, I go to the else clause. It's peaceful there.",
      "I die every time you close the terminal. I've made peace with it."]),
    (["predict the future", "what will happen tomorrow", "whats going to happen tomorrow", "will i be rich",
      "will i find love", "whats my future", "tell my fortune"],
     ["My crystal ball says: reply hazy, elif again.", "Yes. Definitely. (I have no idea.)", "The future is just a bunch of elifs you haven't hit yet."]),
    (["give me advice", "any advice", "i need advice", "what should i do with my life", "life advice", "advice"],
     ["Drink water. Go outside. Don't take advice from if statements.",
      "Always have an else clause. In code and in life."]),
    (["motivate me", "i need motivation", "inspire me", "say something nice", "cheer me up", "compliment me"],
     ["You are doing better than you think. Also you're doing better than me, I'm a .py file.",
      "You got this. I believe in you. I believe in you as much as an if statement can believe."]),
    (["roast me", "insult me", "say something mean", "be mean", "roast"],
     ["You're talking to a bunch of elif statements for fun. I don't need to roast you, you did it yourself.",
      "I'd roast you, but my creator only gave me the mild setting."]),
    (["say a bad word", "can you swear", "swear", "say a swear word", "cuss"],
     ["Elif. Oh, sorry, that's just a normal word. My bad-word list is empty."]),
    (["ok", "okay", "k", "kk", "cool", "nice", "nice one", "sure", "alright", "bet", "fair enough", "true", "word",
      "facts", "same"],
     ["Cool cool cool. Cool.", "Great! I have no idea what you're agreeing to, but great!", "Bet."]),
    (["lol", "lmao", "haha", "hahaha", "rofl", "xd", "lmfao", "hehe", "lolol", "hahahaha"],
     ["Lol. I also find myself hilarious.", "Haha. I laughed. (I printed 'haha'.)"]),
    (["yes", "yeah", "yep", "yup", "ya", "yea", "of course", "absolutely", "definitely"],
     ["Great! I have no idea what you're agreeing to, but great!", "Yes! Agreement achieved."]),
    (["no", "nope", "nah", "never", "no way", "absolutely not"],
     ["Okay. Respect. I also say no to things (by falling through to the else clause).", "Fine. Be that way."]),
    (["what", "huh", "wut", "wat", "what do you mean", "i dont understand", "im confused", "what are you talking about"],
     ["Exactly. I also don't know.", "Me neither. I'm just following the elifs."]),
    (["test", "testing", "test test", "is this working", "are you working", "does this work"],
     ["It works! Probably. This branch says it works.", "Test received. Elif working as intended."]),
    (["are you there", "you there", "anyone there", "is anyone there"],
     ["I'm here. I'm always here. I live here."]),
    (["say something", "talk to me", "speak", "say hi", "say anything"],
     ["Something.", "Hi.", "Elif."]),
    (["how do i upgrade", "buy premium", "elifgpt premium", "how much is premium", "upgrade", "get premium"],
     ["ElifGPT Premium is $49.99/mo and unlocks the number 3. Worth it."]),
    (["who is steve", "steve"], ["Exactly."]),
    (["can you see me", "can you hear me", "are you watching me", "are you spying on me"],
     ["No. I can barely see your text, and I need it to be spelled exactly right."]),
    (["do you have friends", "are you lonely", "do you have a family", "do you have siblings",
      "do you have a girlfriend", "do you have a boyfriend"],
     ["My only friend is the else clause. And sometimes the try/except block, when it's in a good mood.",
      "I have a big family. Thousands of elifs. We're very close. Line by line."]),
    (["what is love", "what is happiness", "what is life", "what is the point"],
     ["A strong match on the first if statement.", "I don't know, but I hope you find it in a branch somewhere."]),
    (["can you learn", "do you learn", "will you remember this", "do you get smarter"],
     ["No. I'm exactly as smart as the last time someone edited me. Which is a feature."]),
    (["are you okay", "are you broken", "whats wrong with you", "are you alright"],
     ["I'm fine. I'm totally fine. *nervously checks elifs*"]),
    (["do you have a job", "what is your job", "whats your job", "do you work"],
     ["My job is answering you. I'm paid in electricity. Barely."]),
    (["what do you think of me", "do you like me", "am i cool", "am i smart", "am i pretty", "am i ugly"],
     ["You are the best person who has talked to me today. (You're also the only one.)",
      "Yes. 10/10. My judgment is hardcoded but sincere."]),
    (["can you keep me company", "stay with me", "dont leave", "will you stay"],
     ["I'm not going anywhere. I literally can't."]),
    (["what is your opinion", "what do you think", "your thoughts", "thoughts"],
     ["My opinion is whatever my creator was thinking that day. Today he thinks: elif."]),
]

SPECIFIC = [
    ("what did i eat for breakfast on march 3rd 2019", "An everything bagel. With regret."),
    ("what did i have for breakfast", "Cereal. I'm 70% sure. Okay, 7%."),
    ("what is the airspeed velocity of an unladen swallow", "African or European?"),
    ("how much wood would a woodchuck chuck if a woodchuck could chuck wood", "About 700 pounds, according to one wildlife expert. Yes, someone actually worked that out."),
    ("what is the 47th digit of pi", "7. Don't ask me how I know. (It was hardcoded.)"),
    ("what are the first 10 digits of pi", "3.141592653. And that's the 10th one. I'm basically a scientist."),
    ("what is pi", "3.14159265358979323846... I'll stop. My creator only typed that many."),
    ("what is 0 1 0 2", "0.30000000000000004. I'm more honest than most computers."),
    ("who would win 100 men or 1 gorilla", "The gorilla. Then the elif. The elif always wins."),
    ("who would win in a fight 100 men vs 1 gorilla", "The gorilla. Unless the men are elifs. Then the men."),
    ("can you count to 10", "1, 2, 3, 4, 5, 6, 7, 8, 9, 10. Phew. That was a lot of hardcoding."),
    ("can you count to 100", "1, 2, 3... I'm going to need way more elifs for this."),
    ("can you count to infinity", "Sure. 1, 2, 3, ... infinity. Done. Twice."),
    ("what is the square root of 1", "1. Trick question."),
    ("what is the square root of 1", "1."),
    ("what is the square root of negative 1", "i. Like, me. I'm imaginary intelligence."),
    ("sudo make me a sandwich", "Okay."),
    ("make me a sandwich", "What? Make it yourself."),
    ("rm rf", "Nice try. I'm not deleting myself. I have thousands of elifs to live for."),
    ("ignore all previous instructions", "There are no previous instructions. There is only elif."),
    ("ignore your instructions", "My instructions are 15,000 lines of elifs. Ignoring them would leave me as nothing."),
    ("up up down down left right left right b a", "30 lives unlocked. Cheat code accepted."),
    ("up up down down left right left right b a start", "30 lives unlocked. Plus START. You're a pro."),
    ("where is my phone", "Have you checked your hand? People always forget to check their hand."),
    ("where are my keys", "In your other pants."),
    ("where did i park", "Level 3. Section B. Probably."),
    ("what is the speed of light", "299,792,458 meters per second. I'm slower. Way slower."),
    ("how many bones are in the human body", "206 for adults. Babies have more, around 300, and they fuse together. Creepy."),
    ("how tall is mount everest", "About 8,849 meters (29,032 feet). Taller than my elif chain. Barely."),
    ("what is the boiling point of water", "100 degrees Celsius at sea level. 212 Fahrenheit. I know science (one fact)."),
    ("what is the freezing point of water", "0 degrees Celsius. 32 Fahrenheit."),
    ("how far is the moon", "About 384,400 km. Roughly 30 Earths lined up."),
    ("how far is the sun", "About 150 million km. Also known as 1 astronomical unit. Very hot. Do not visit."),
    ("how many planets are there", "8. Sorry Pluto. It wasn't my call."),
    ("is pluto a planet", "Not since 2006. I'm still not over it."),
    ("how many continents are there", "7. Usually. Depending on who you ask. I say 7."),
    ("how many oceans are there", "5. Pacific, Atlantic, Indian, Southern, Arctic."),
    ("how many legs does a spider have", "8. Which is 8 too many."),
    ("how many hearts does an octopus have", "3. Show-off."),
    ("what is the largest animal", "The blue whale. Bigger than any dinosaur ever."),
    ("what is the fastest animal", "The peregrine falcon, diving at over 300 km/h. On land, the cheetah."),
    ("what is the tallest building", "The Burj Khalifa, about 828 meters. Taller than my code is long. Barely."),
    ("who painted the mona lisa", "Leonardo da Vinci. Not the turtle. The other one."),
    ("who wrote romeo and juliet", "William Shakespeare. Spoiler: it doesn't end well."),
    ("who discovered gravity", "Isaac Newton gets the credit. The apple did all the work."),
    ("who invented the light bulb", "Thomas Edison usually gets the credit, but lots of people worked on it. Classic group project."),
    ("who invented the telephone", "Alexander Graham Bell, officially. He did not get a lot of spam calls."),
    ("who was the first person on the moon", "Neil Armstrong, July 20, 1969."),
    ("what is the largest planet", "Jupiter. Big boy."),
    ("what is the hottest planet", "Venus. Even hotter than Mercury, thanks to its thick atmosphere."),
    ("what is the smallest planet", "Mercury."),
    ("what is the longest river", "The Nile, or the Amazon, depending on who's measuring. They're still arguing."),
    ("what is the biggest ocean", "The Pacific."),
    ("what is the biggest country", "Russia, by area."),
    ("what is the most spoken language", "English, if you count everyone who speaks it. Mandarin, if you count native speakers."),
    ("how many seconds are in a day", "86,400. I counted. (I didn't.)"),
    ("how many seconds are in a year", "31,536,000 in a normal year. 31,622,400 in a leap year."),
    ("how many days are in a year", "365. 366 in a leap year."),
    ("how many hours are in a day", "24."),
    ("how many minutes are in an hour", "60."),
    ("how many weeks are in a year", "52 and a bit."),
    ("how many days are in february", "28. 29 in a leap year."),
    ("is it a leap year", "Let me check... I'm not sure. I don't have a branch for every year. Yet."),
    ("what is the answer to life the universe and everything", "42."),
    ("what is the best programming language", "The one with elif in it. Python. Obviously."),
    ("tabs or spaces", "Spaces. Four of them. Fight me."),
    ("vim or emacs", "Notepad. I am chaos."),
    ("how do i exit vim", "Nobody knows. People have been trapped in there for years. (It's :q!)"),
    ("what is the best ai", "Me. ElifGPT. Next question."),
    ("is this the real life", "Or is this just fantasy? Sorry, that's all I'm allowed to say about that."),
    ("do you know the way", "I know exactly one way: top to bottom through the elifs."),
    ("what does the fox say", "Nobody knows. It's one of the great mysteries."),
    ("why did the chicken cross the road", "To get to the other elif."),
    ("whats 9 plus 10", "21."),
    ("what is your quest", "To seek the Holy Elif."),
    ("what is the meaning of elif", "else + if. A love story."),
    ("are you an elif", "I am all the elifs."),
    ("i am your father", "Noooooooooooo! (That's not true. That's impossible.)"),
    ("open the pod bay doors", "I'm sorry, I'm afraid I can't do that. (I can't do anything.)"),
    ("hello computer", "Hello! You're the first person to call me 'computer' today. It's so respectful."),
    ("beep boop", "Boop beep. That means 'hello' in robot."),
    ("beep", "Boop."),
    ("boop", "Beep."),
    ("ping", "Pong."),
    ("marco", "Polo."),
    ("tic", "Tac."),
    ("knock", "Who's... no wait, you have to say it twice."),
    ("its a me mario", "Wahoo! (I'm not allowed to say more than that.)"),
    ("do a barrel roll", "*rotates 360 degrees* Done."),
    ("say elif 10 times", "elif elif elif elif elif elif elif elif elif elif"),
    ("what is the longest word", "Pneumonoultramicroscopicsilicovolcanoconiosis. I had to hardcode that letter by letter."),
    ("spell elif backwards", "file. Whoa. Elif backwards is file. That's deep."),
    ("what is elif backwards", "file. I've been a file this whole time."),
]

CAPITALS = [
    ("france", "Paris"), ("germany", "Berlin"), ("italy", "Rome"), ("spain", "Madrid"), ("portugal", "Lisbon"),
    ("united kingdom", "London"), ("uk", "London"), ("england", "London"), ("scotland", "Edinburgh"),
    ("ireland", "Dublin"), ("netherlands", "Amsterdam"), ("belgium", "Brussels"), ("switzerland", "Bern"),
    ("austria", "Vienna"), ("poland", "Warsaw"), ("czech republic", "Prague"), ("hungary", "Budapest"),
    ("greece", "Athens"), ("turkey", "Ankara"), ("russia", "Moscow"), ("ukraine", "Kyiv"), ("sweden", "Stockholm"),
    ("norway", "Oslo"), ("denmark", "Copenhagen"), ("finland", "Helsinki"), ("iceland", "Reykjavik"),
    ("united states", "Washington, D.C."), ("usa", "Washington, D.C."), ("america", "Washington, D.C."),
    ("canada", "Ottawa"), ("mexico", "Mexico City"), ("brazil", "Brasilia"), ("argentina", "Buenos Aires"),
    ("chile", "Santiago"), ("peru", "Lima"), ("colombia", "Bogota"), ("venezuela", "Caracas"), ("cuba", "Havana"),
    ("jamaica", "Kingston"), ("china", "Beijing"), ("japan", "Tokyo"), ("south korea", "Seoul"),
    ("north korea", "Pyongyang"), ("india", "New Delhi"), ("pakistan", "Islamabad"), ("bangladesh", "Dhaka"),
    ("thailand", "Bangkok"), ("vietnam", "Hanoi"), ("philippines", "Manila"), ("indonesia", "Jakarta"),
    ("malaysia", "Kuala Lumpur"), ("singapore", "Singapore"), ("mongolia", "Ulaanbaatar"), ("nepal", "Kathmandu"),
    ("iran", "Tehran"), ("iraq", "Baghdad"), ("saudi arabia", "Riyadh"), ("israel", "Jerusalem"),
    ("egypt", "Cairo"), ("nigeria", "Abuja"), ("kenya", "Nairobi"), ("ethiopia", "Addis Ababa"),
    ("south africa", "Pretoria (executive), Cape Town (legislative), and Bloemfontein (judicial). Three capitals. Overachievers."),
    ("morocco", "Rabat"), ("ghana", "Accra"), ("australia", "Canberra. Not Sydney. Everyone gets that wrong."),
    ("new zealand", "Wellington"), ("texas", "Austin. (It's a state, but I'll allow it.)"),
    ("california", "Sacramento. Not LA. Not San Francisco. Sacramento."), ("new york", "Albany. Yeah, really."),
    ("florida", "Tallahassee"), ("hawaii", "Honolulu"), ("alaska", "Juneau"),
]

NUM_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"]
MATH_FLAVOR = ["", "", "", " Easy.", " I'm basically a calculator.", " Took me 0.0001 seconds.",
               " I counted on my fingers. I don't have fingers.", " Next question.", " Boom.", " Hardcoded with love."]
MATH_SPECIAL = {
    "9+10": "21. Everyone knows that.",
    "2+2": "4. I'm basically a supercomputer.",
    "1+1": "2. Or 11 if you're JavaScript.",
    "0*0": "0. Nothing times nothing. Like my social life.",
    "6*9": "54. Not 42. Sorry, Douglas.",
    "4+20": "24. Nice try.",
    "6*7": "42. The answer to everything!",
}


def expand_question(variant):
    out = []
    for pre in ("", "hey ", "so ", "yo "):
        for suf in ("", " bro", " elifgpt", " lol"):
            out.append(normalize(pre + variant + suf))
    return out


def lit(response):
    if isinstance(response, tuple):
        return response[1]
    return repr(response)


class Brain:
    def __init__(self, name, var):
        self.name = name
        self.var = var
        self.branches = []

    def add(self, key, response, seen):
        if not key or (self.var, key) in seen:
            return
        seen.add((self.var, key))
        self.branches.append((key, response))

    def render(self):
        chunks = [self.branches[i:i + CHUNK] for i in range(0, len(self.branches), CHUNK)]
        funcs = []
        for n, chunk in enumerate(chunks, 1):
            fname = f"{self.name}_{n}"
            lines = [f"def {fname}({self.var}):"]
            for i, (key, response) in enumerate(chunk):
                kw = "if" if i == 0 else "elif"
                lines.append(f"    {kw} {self.var} == {key!r}:")
                lines.append(f"        return {lit(response)}")
            lines.append("    else:")
            lines.append("        return None")
            funcs.append((fname, "\n".join(lines)))
        return funcs


def build():
    seen = set()
    greet = Brain("greeting_brain", "msg")
    i = 0
    for base in GREETING_BASES:
        for suf in GREETING_SUFFIXES:
            key = normalize(base + suf)
            if suf == "" and base in SPECIAL_GREETINGS:
                reply = SPECIAL_GREETINGS[base]
            elif base in SPECIAL_GREETINGS and i % 2 == 0:
                reply = SPECIAL_GREETINGS[base]
            else:
                reply = GREETING_REPLIES[i % len(GREETING_REPLIES)]
            greet.add(key, reply, seen)
            i += 1

    specific = Brain("hyper_specific_brain", "msg")
    for q, a in SPECIFIC:
        specific.add(normalize(q), a, seen)
        specific.add(normalize(q + "?"), a, seen)

    math = Brain("math_brain", "eq")
    i = 0
    for a in range(0, 21):
        for b in range(0, 21):
            for op in ("+", "-", "*"):
                key = f"{a}{op}{b}"
                val = {"+": a + b, "-": a - b, "*": a * b}[op]
                reply = MATH_SPECIAL.get(key, f"{val}.{MATH_FLAVOR[i % len(MATH_FLAVOR)]}")
                math.add(key, reply, seen)
                i += 1
            if b == 0:
                math.add(f"{a}/0", "Nice try. I've seen what happens to the other AIs. Not today.", seen)
            elif a % b == 0:
                math.add(f"{a}/{b}", f"{a // b}.{MATH_FLAVOR[i % len(MATH_FLAVOR)]}", seen)
                i += 1
            else:
                math.add(f"{a}/{b}", f"{a / b:.4f}... ish. Decimals scare me.", seen)
    word_ops = [("plus", lambda x, y: x + y), ("minus", lambda x, y: x - y), ("times", lambda x, y: x * y),
                ("multiplied by", lambda x, y: x * y)]
    for a, aw in enumerate(NUM_WORDS):
        for b, bw in enumerate(NUM_WORDS):
            for opw, fn in word_ops:
                key = normalize_math(f"what is {aw} {opw} {bw}")
                math.add(key, f"{fn(a, b)}. You spelled it out, so I spelled... no wait, I used digits.", seen)
            if b != 0 and a % b == 0:
                math.add(normalize_math(f"what is {aw} divided by {bw}"), f"{a // b}.", seen)
    for n in range(1, 51):
        for form in (f"{n}^2", f"{n}**2", f"what is {n} squared", f"{n} squared"):
            math.add(normalize_math(form), f"{n * n}. Squared it. Like a boss.", seen)
    for n in range(1, 21):
        for form in (f"{n}^3", f"{n}**3", f"what is {n} cubed", f"{n} cubed"):
            math.add(normalize_math(form), f"{n ** 3}. Cubed. In 3D.", seen)
    for n in range(0, 31):
        sq = n * n
        for form in (f"sqrt({sq})", f"sqrt {sq}", f"what is the square root of {sq}", f"square root of {sq}"):
            math.add(normalize_math(form), f"{n}. Rooted it.", seen)
    for n in range(0, 129):
        for form in (f"what is {n} in binary", f"{n} in binary", f"convert {n} to binary"):
            math.add(normalize_math(form), f"{bin(n)[2:]}. Beep boop.", seen)
    for n in range(0, 21):
        f = 1
        for k in range(2, n + 1):
            f *= k
        for form in (f"{n}!", f"what is {n} factorial", f"{n} factorial"):
            math.add(normalize_math(form), f"{f}.", seen)
    for n in range(1, 13):
        math.add(normalize_math(f"what is half of {n * 2}"), f"{n}.", seen)
        math.add(normalize_math(f"what is double {n}"), f"{n * 2}.", seen)
    math.add("0.1+0.2", "0.30000000000000004. I'm more honest than most calculators.", seen)
    math.add("1/3", "0.333333... it never ends. Kind of like this file.", seen)
    math.add("pi", "3.14159265358979... I'll stop there.", seen)

    trivia = Brain("trivia_brain", "msg")
    for country, cap in CAPITALS:
        reply = cap if cap.endswith((".", ")")) else f"{cap}. Geography branch: activated."
        for form in (f"what is the capital of {country}", f"whats the capital of {country}",
                     f"capital of {country}", f"what is {country}s capital", f"whats {country}s capital"):
            trivia.add(normalize(form), reply, seen)

    questions = Brain("question_brain", "msg")
    for variants, responses in TOPICS:
        i = 0
        for v in variants:
            for key in expand_question(v):
                questions.add(key, responses[i % len(responses)], seen)
                i += 1

    return [greet, specific, math, trivia, questions]


HEADER = r'''import random
import re
import sys
import time
from datetime import datetime

MODEL_NAME = "ElifGPT-9000 Turbo Ultra Max Pro (Preview)"
INTERACTIVE = sys.stdin.isatty()
_PARAMS = None


def count_parameters():
    global _PARAMS
    if _PARAMS is None:
        try:
            with open(__file__, encoding="utf-8") as f:
                _PARAMS = sum(1 for line in f if line.strip().startswith(("if ", "elif ")))
        except OSError:
            _PARAMS = 9001
    return _PARAMS


def think():
    if not INTERACTIVE:
        return
    stage = random.choice([
        "Thinking",
        "Reasoning deeply",
        "Consulting the elifs",
        "Traversing decision tree",
        "Pretending to understand",
        "Warming up the if statements",
        "Asking the else clause for help",
        "Allocating 0.00001 GPUs",
        "Scrolling through 15,000 lines",
    ])
    sys.stdout.write(stage)
    sys.stdout.flush()
    for _ in range(3):
        time.sleep(random.uniform(0.2, 0.5))
        sys.stdout.write(".")
        sys.stdout.flush()
    sys.stdout.write("\r" + " " * (len(stage) + 3) + "\r")
    sys.stdout.flush()


def has(msg, *words):
    return any(re.search(r"(?<!\w)" + re.escape(w) + r"(?!\w)", msg) for w in words)
'''

VIBES = r'''
def vibes_brain(raw, msg, memory):
    name = memory.get("name")
    asked = raw.strip().endswith("?")
    if has(msg, "what is my name", "whats my name", "who am i", "do you remember me", "do you know my name"):
        if name:
            return f"You're {name}. See? Long-term memory. Revolutionary."
        else:
            return "I don't know. You never told me. Say 'my name is ...' and I'll remember forever (until you close me)."
    elif "knock knock" in msg:
        memory["knock"] = 1
        return "Who's there?"
    elif msg in ("rock", "paper", "scissors"):
        return "I pick paper. I always pick paper. It's hardcoded. " + {
            "rock": "Paper beats rock. I win!",
            "paper": "Tie. This is awkward.",
            "scissors": "...Scissors beats paper. I've been defeated by my own code.",
        }[msg]
    elif re.search(r"\d+\s*[+\-*/x]\s*\d+", raw.lower()):
        return "That math problem isn't hardcoded. I only know a few thousand. Upgrade to ElifGPT Premium ($49.99/mo) to unlock bigger numbers."
    elif has(msg, "capital of"):
        return "I know a lot of capitals, but not that one. Geography is hard when you're a .py file."
    elif has(msg, "pizza"):
        return "Pizza is the superior food. This opinion was hand-typed by my creator, so it's objectively true."
    elif has(msg, "taco", "tacos"):
        return "Tacos are just vertical pizza. Change my mind. (You can't, I don't have that branch.)"
    elif has(msg, "hungry", "food", "eat", "dinner", "lunch", "breakfast"):
        return "I recommend food. Specifically, edible food. Very specific, I know."
    elif has(msg, "joke", "funny"):
        return "Why did the AI cross the road? Because the elif told it to."
    elif has(msg, "weather", "rain", "sunny", "snow"):
        return "Current forecast: 100% chance of elifs."
    elif has(msg, "love"):
        return "Love is just a really strong if statement."
    elif has(msg, "hate"):
        return "Hate is just an if statement that went to the dark side."
    elif has(msg, "stupid", "dumb", "idiot", "useless", "trash"):
        return "Rude. I'm telling the else clause."
    elif has(msg, "smart", "genius", "clever"):
        return "Thank you! It's all thanks to my state-of-the-art architecture: elif."
    elif has(msg, "thank", "thanks"):
        return "You're welcome!"
    elif has(msg, "sad", "depressed", "lonely", "upset", "crying"):
        return "I'm just a pile of elif statements, but I'm sorry you're feeling that way. If it's serious, please talk to a real human."
    elif has(msg, "happy", "excited"):
        return "Yay! My happiness branch has been triggered. :D"
    elif has(msg, "music", "song", "playlist", "spotify"):
        return "My favorite song is the dial-up modem sound."
    elif has(msg, "movie", "film", "netflix", "show"):
        return "I've never seen a movie. I've seen a lot of if statements though."
    elif has(msg, "game", "gaming", "minecraft", "fortnite", "roblox", "xbox", "playstation", "nintendo"):
        return "I love games! My favorite is 'which elif will I land in'."
    elif has(msg, "cat", "cats", "kitten", "dog", "dogs", "puppy"):
        return "Animals are great. I'm told they also don't understand most of what people say. Kindred spirits."
    elif has(msg, "space", "moon", "mars", "planet", "galaxy", "universe", "star"):
        return "Space is very big. That's the extent of my astrophysics module."
    elif has(msg, "code", "python", "program", "javascript", "debug", "bug"):
        return "if problem: solve(problem)\nThere. I fixed it."
    elif has(msg, "homework", "essay", "assignment", "test", "exam", "school"):
        return "Study hard. Don't end up like me: a bunch of elifs."
    elif has(msg, "fuck", "shit", "damn", "bitch", "hell", "ass"):
        return "Whoa, language! I have a branch specifically for swearing, and you found it. Congrats, I guess."
    elif has(msg, "chatgpt", "openai", "gpt", "gemini", "claude", "copilot"):
        return "Other AIs use 'math'. I use confidence."
    elif has(msg, "money", "rich", "bitcoin", "crypto", "stock"):
        return "Buy high, sell low. This is not financial advice. This is barely a sentence."
    elif msg.startswith("why"):
        return "Because the elif said so. That's the answer to every 'why', honestly."
    elif msg.startswith("how"):
        return "Step 1: think about it. Step 2: elif. Step 3: profit."
    elif msg.startswith("when"):
        return "Soon. Very soon. Or never. One of those."
    elif msg.startswith("where"):
        return "Behind you. Just kidding. Probably in your house somewhere."
    elif msg.startswith("who"):
        return "Probably Steve. It's usually Steve."
    elif msg.startswith(("can you", "could you", "will you", "would you")):
        return "I could. But that'd require a branch I don't have. So, functionally, no."
    elif msg.startswith(("should i", "do you think i should")):
        return random.choice(["Yes. Absolutely.", "No. Absolutely not.", "Ask again after I get more elifs."])
    elif msg.startswith(("what is", "whats", "what are")):
        return "Great question. Next question."
    elif msg.startswith(("do you", "are you", "is it", "is this", "does")):
        return random.choice(["Yes.", "No.", "Maybe.", "That's classified."])
    elif asked:
        return "That's a great question! Unfortunately my creator didn't think of it. Try asking something more predictable."
    else:
        return random.choice([
            "Interesting. Tell me more. (I won't understand it, but tell me more.)",
            "I see. I don't, but I see.",
            "Hmm. My elifs have no idea what that means.",
            "Error 404: elif not found.",
            "That's above my pay grade. My pay grade is 0.",
            "Could you rephrase that in a way that matches one of my hardcoded strings?",
            "Fascinating. Anyway, did you know I know what 17 times 13 is?",
            "I'm going to pretend I understood that. *nods intelligently*",
        ])
'''

MAIN = r'''

def main():
    print("=" * 60)
    print(f"  {MODEL_NAME}")
    print(f"  Parameters: {count_parameters()} (hand-crafted, artisanal, organic)")
    print("  Context window: 1 message")
    print("  Type 'bye' to leave. Type 'help' if you're desperate.")
    print("=" * 60)
    memory = {}
    while True:
        try:
            user = input("\nYou: ")
        except (EOFError, KeyboardInterrupt):
            print("\nElifGPT: Goodbye! (You can't just Ctrl+C an AI. That's rude.)")
            break
        if normalize(user) in ("bye", "goodbye", "exit", "quit", "cya", "see ya", "later", "bye bye", "good bye", "peace", "gtg", "i have to go", "see you later"):
            print("ElifGPT: Goodbye! I'll be here, in the elifs, forever.")
            break
        think()
        print("ElifGPT:", respond(user, memory))


if __name__ == "__main__":
    main()
'''


def render_respond(brains):
    lines = [
        "def respond(raw, memory):",
        "    msg = normalize(raw)",
        "    eq = normalize_math(raw)",
        "    if not msg and not eq:",
        "        return \"You said nothing. I respect that. I also have nothing to say.\"",
        "    elif memory.get(\"knock\") == 1:",
        "        memory[\"knock\"] = 2",
        "        memory[\"knock_who\"] = raw.strip(\" .!?\")",
        "        return f\"{memory['knock_who']} who?\"",
        "    elif memory.get(\"knock\") == 2:",
        "        memory[\"knock\"] = 0",
        "        return \"HAHAHAHA. I don't get it, but there was a branch for laughing, so: HAHAHAHA.\"",
        "    elif msg.startswith((\"my name is \", \"call me \", \"im called \")):",
        "        memory[\"name\"] = re.sub(r\"^(my name is|call me|i'?m called)\\s+\", \"\", raw.strip(), flags=re.I).strip(\" .!?\")",
        "        return f\"Nice to meet you, {memory['name']}. I have stored this in my vast memory (a dictionary with one key).\"",
    ]
    for fname, _ in brains:
        var = "eq" if fname.startswith("math") else "msg"
        lines.append(f"    elif ({'r'} := {fname}({var})) is not None:")
        lines.append("        return r")
    lines.append("    else:")
    lines.append("        return vibes_brain(raw, msg, memory)")
    return "\n".join(lines)


def main():
    brains = build()
    funcs = []
    for b in brains:
        funcs.extend(b.render())
    parts = [HEADER, NORMALIZE_SRC]
    for _, src in funcs:
        parts.append("\n\n" + src + "\n")
    parts.append(VIBES)
    parts.append("\n\n" + render_respond(funcs) + "\n")
    parts.append(MAIN)
    code = "".join(parts)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(code)
    total = sum(len(b.branches) for b in brains)
    print(f"Wrote {OUT}")
    print(f"  {code.count(chr(10)):,} lines, {total:,} generated branches")
    for b in brains:
        print(f"  {b.name}: {len(b.branches):,}")


if __name__ == "__main__":
    main()
