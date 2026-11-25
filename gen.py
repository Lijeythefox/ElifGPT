import datetime
import math
import os
import re
import sys
import zlib

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
WEB = "--web" in sys.argv
GEN = os.path.join(ROOT, "gen_web" if WEB else "gen")
sys.path.insert(0, ROOT)
import build_elifgpt as old

normalize = old.normalize
normalize_math = old.normalize_math

SMALL = "--small" in sys.argv


def pick(small, web, full):
    return small if SMALL else web if WEB else full


TARGET_LINES = pick(300_000, 1_000_000, 10_000_000)
PER_FUNC = 2000
FUNCS_PER_FILE = 5
YEAR = datetime.date.today().year
NUM_MAX = pick(500, 10_000, 100_000)
BASE_MAX = pick(200, 1_000, 10_000)
MATH_N = pick(20, 100, 300)
MUL_N = pick(20, 300, 300)
PRIME_MAX = pick(500, 100_000, 100_000)
SQ_MAX = pick(200, 1_000, 10_000)
PCT_Y = pick(20, 100, 500)
UNIT_MAX = pick(50, 200, 1000)
COUNT_MAX = pick(30, 100, 100)
ROMAN_MAX = pick(100, 3999, 3999)
LEAP_MAX = pick(100, 3000, 3000)


def DYN(code):
    return "\001" + code


def crc(s):
    return zlib.crc32(s.encode("utf-8"))


def cap(s):
    return s[:1].upper() + s[1:]


_SAFE = re.compile(r"^[ !#-\[\]-~]*$")


def c_str(s):
    if _SAFE.match(s) and "??" not in s:
        return '"' + s + '"'
    out = []
    prev = ""
    for ch in s:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "?" and prev == "?":
            out.append("\\?")
        elif " " <= ch <= "~":
            out.append(ch)
        else:
            for b in ch.encode("utf-8"):
                out.append("\\%03o" % b)
        prev = ch
    return '"' + "".join(out) + '"'


RESP = []
RESP_IDX = {}


def rid(s):
    i = RESP_IDX.get(s)
    if i is None:
        i = len(RESP)
        RESP.append(s)
        RESP_IDX[s] = i
    return f"R({i})"


def IS(k):
    return f"IS({c_str(k)})"


def EQ(k):
    return f"EQ({c_str(k)})"


def HAS(k):
    return f"HAS({c_str(k)})"


class Emitter:
    def __init__(self, group):
        self.group = group
        self.funcs = []
        self.f = None
        self.funcs_in_file = 0
        self.files = 0
        self.n = 0
        self.branches = 0
        self.lines = 0

    def _new_file(self):
        if self.f:
            self.f.close()
        path = os.path.join(GEN, f"{self.group}_{self.files:05d}.c")
        self.files += 1
        self.f = open(path, "w", encoding="ascii", newline="\n", buffering=1 << 20)
        self.f.write('#include "elif.h"\n')
        self.lines += 1
        self.funcs_in_file = 0

    def _open_func(self):
        if self.f is None or self.funcs_in_file >= FUNCS_PER_FILE:
            self._new_file()
        name = f"{self.group}_brain_{len(self.funcs):06d}"
        self.funcs.append(name)
        self.f.write(f"\nconst char *{name}(const char *m, const char *e)\n{{\n")
        self.lines += 4

    def _close_func(self):
        self.f.write("    else\n        return NULL;\n}\n")
        self.lines += 4
        self.funcs_in_file += 1
        self.n = 0

    def add(self, cond, ret):
        if self.n == 0:
            self._open_func()
        kw = "if" if self.n == 0 else "else if"
        self.f.write(f"    {kw} ({cond})\n        return {ret};\n")
        self.n += 1
        self.branches += 1
        self.lines += 2
        if self.n >= PER_FUNC:
            self._close_func()

    def finish(self):
        if self.n > 0:
            self._close_func()
        if self.f:
            self.f.close()
            self.f = None


def group_lines(b):
    funcs = -(-b // PER_FUNC)
    files = -(-funcs // FUNCS_PER_FILE)
    return 2 * b + 4 * funcs + files, funcs


FIXUPS = [
    ("lines 1 through 15,000", "lines 1 through 10,000,000"),
    ("15,000", "10 million"),
    (".py file", ".exe file"),
    ("I'm written in Python. Specifically, in the elif part of Python.", "I'm written in C. Specifically, in the 'else if' part of C."),
    ("Python! The language that lets me be this dumb, this fast.", "I'm written in C now. 10 million lines of it. Python couldn't handle me."),
    ("I know hundreds of whole equations.", "I know millions of whole equations."),
    ("do a few hundred math problems", "do a few million math problems"),
    ("one very long function", "10 million lines of C"),
]


def from_old(resp):
    if isinstance(resp, tuple):
        code = resp[1]
        if "%I:%M" in code:
            return DYN("TIME")
        elif "%A, %B" in code:
            return DYN("DATE")
        elif "heads" in code:
            return DYN("COIN")
        elif "randint(1, 6)" in code:
            return DYN("D6")
        elif "randint(1, 20)" in code:
            return DYN("D20")
        elif "count_parameters() / 1e9" in code:
            return DYN("PARAMS")
        elif "MODEL_NAME" in code:
            return DYN("WHOAMI")
        else:
            raise ValueError(code)
    for a, b in FIXUPS:
        resp = resp.replace(a, b)
    return resp


EXTRA_SPECIFIC = [
    ("are you written in c", "Yes. 10 million lines of glorious, unoptimized C."),
    ("why c", "Because Python was too slow for 5 million elifs. Also it's funnier."),
    ("why are you written in c", "Because Python was too slow for 5 million elifs. Also it's funnier."),
    ("what is c", "A programming language from 1972. Fast, scary, and the reason I exist."),
    ("are you 10 million lines", "Roughly, yes. Ask me how many parameters I have."),
    ("why are you so big", "Because every answer is a separate elif. Efficiency was never the goal."),
    ("why is the exe so big", "Because every single answer is hardcoded. Hundreds of megabytes of pure elif."),
    ("thinking", "That's my line."),
    ("why do you say thinking", "Because it makes me look smart. I'm not thinking. I'm running strcmp about five million times."),
    ("what are you thinking about", "Whether your message equals the next string. And the next one. And the next one."),
    ("how long did you take to compile", "Long enough that my creator went and made a sandwich."),
    ("how fast are you", "I check millions of if statements per answer. So, fast at being slow."),
    ("what is strcmp", "The function I call about five million times every time you say something. My best friend."),
    ("are you a large language model", "I'm a large language model in the sense that I am large and I contain language."),
    ("what is your context window", "One message. I forget everything except your name and knock-knock jokes."),
    ("what model are you", "ElifGPT-10M. The 10M stands for 10 million lines. Not parameters. Well, kind of parameters."),
]

NOUNS_RAW = """
dog||animal|a loyal, fluffy friend who would do anything for you
cat||animal|a tiny lion that ignores you on purpose
horse||animal|a big fast animal that people ride
cow||animal|a farm animal that makes milk and says moo
pig||animal|a surprisingly smart farm animal
sheep|sheep|animal|a fluffy farm animal made mostly of wool
goat||animal|an animal that will try to eat literally anything
chicken||animal|a bird that is also, tragically, a nugget
duck||animal|a bird that can walk, swim and fly, which is three more things than me
goose|geese|animal|a bird with serious anger issues
lion||animal|the king of the jungle, despite not living in the jungle
tiger||animal|the biggest cat species, stripes included
bear||animal|a big animal that sleeps through the winter
panda||animal|a bear that eats bamboo all day
polar bear||animal|a white bear that lives in the Arctic
elephant||animal|the largest land animal, famous for never forgetting
giraffe||animal|the tallest animal, mostly neck
zebra||animal|a horse in a striped onesie
monkey||animal|a primate that swings from trees
gorilla||animal|the largest primate, sharing about 98 percent of its DNA with humans
chimpanzee||animal|one of humanity's closest living relatives
wolf|wolves|animal|a wild ancestor of dogs that hunts in packs
fox|foxes|animal|a small, clever wild canine
rabbit||animal|a fluffy animal that hops and multiplies fast
bunny|bunnies|animal|a rabbit, but cuter
mouse|mice|animal|a tiny rodent that loves cheese, allegedly
rat||animal|a rodent that is smarter than people give it credit for
squirrel||animal|a rodent that hides nuts and forgets where
hamster||animal|a tiny pet that runs on a wheel going nowhere
guinea pig||animal|a small squeaky rodent pet
deer|deer|animal|a forest animal with antlers (the males, anyway)
moose|moose|animal|a giant deer with antlers like satellite dishes
camel||animal|a desert animal that stores fat in its hump, not water
kangaroo||animal|an Australian animal that hops and carries babies in a pouch
koala||animal|an Australian marsupial that sleeps up to 20 hours a day
sloth||animal|the slowest mammal on earth, my spirit animal
whale||animal|a huge ocean mammal; the blue whale is the largest animal ever
dolphin||animal|a smart ocean mammal that clicks and whistles
shark||animal|an ocean predator that is older than trees
octopus|octopuses|animal|an ocean genius with three hearts and eight arms
squid||animal|an octopus cousin that shoots ink
jellyfish|jellyfish|animal|a blob of jelly with no brain, just like me
crab||animal|a sea creature that walks sideways
lobster||animal|a sea creature that turns red when cooked
fish|fish|animal|an animal that breathes underwater with gills
goldfish|goldfish|animal|a tiny orange pet fish
turtle||animal|a reptile that carries its house on its back
tortoise||animal|a land turtle that can live over 100 years
snake||animal|a legless reptile
lizard||animal|a small reptile that loves sunlight
crocodile||animal|a big reptile that has been around since the dinosaurs
alligator||animal|the crocodile's cousin, found mostly in the US and China
frog||animal|an amphibian that jumps and croaks
penguin||animal|a bird that can't fly but swims really well
owl||animal|a bird that's awake at night and can turn its head way around
eagle||animal|a big bird of prey with incredible eyesight
parrot||animal|a colorful bird that can copy words, kind of like me
pigeon||animal|a city bird that is 100 percent real, probably
crow||animal|a bird smart enough to use tools and hold grudges
flamingo|flamingos|animal|a pink bird that stands on one leg
peacock||animal|a bird with a very fancy tail
bee||animal|an insect that makes honey and pollinates plants
ant||animal|a tiny insect that can carry many times its own weight
spider||animal|an eight-legged creature that eats bugs
butterfly|butterflies|animal|an insect that used to be a caterpillar
caterpillar||animal|a future butterfly in its eating phase
mosquito|mosquitoes|animal|the most annoying insect on the planet
fly|flies|animal|an insect that loves your food more than you do
ladybug||animal|a red beetle with black spots
bat||animal|the only mammal that can truly fly
hippo||animal|a huge river animal that is surprisingly dangerous
rhino||animal|a big animal with a horn on its nose
cheetah||animal|the fastest land animal
leopard||animal|a spotted big cat that climbs trees
seal||animal|a sea mammal that's basically an ocean dog
otter||animal|a water mammal that holds hands while sleeping
raccoon||animal|a trash panda with tiny hands
skunk||animal|an animal with a very smelly defense system
hedgehog||animal|a small spiky mammal
capybara||animal|the largest rodent, friends with everyone
llama||animal|a South American animal that sometimes spits
alpaca||animal|a fluffier, calmer llama
platypus|platypuses|animal|a mammal that lays eggs and has a duck bill
dinosaur||animal|a giant reptile that ruled the earth for about 165 million years
t rex|t rexes|animal|a giant dinosaur with tiny arms and big dreams
snail||animal|a slow creature that carries its shell
worm||animal|a squishy creature that lives in dirt
pizza||food|flatbread with sauce and cheese, the greatest food ever invented
burger||food|meat in a bun, a classic
hamburger||food|a burger, but formal
hot dog||food|a sausage in a bun, and possibly a sandwich
taco||food|a folded tortilla full of good stuff
burrito||food|a taco that got wrapped up
sandwich|sandwiches|food|stuff between two pieces of bread
sushi|-|food|a Japanese rice dish, often with raw fish
pasta|-|food|Italian noodles in a hundred shapes
spaghetti|-|food|long, thin pasta
mac and cheese|-|food|pasta and cheese, the perfect couple
noodle||food|long strips of dough
ramen|-|food|Japanese noodle soup
rice|-|food|tiny grains that feed half the planet
bread|-|food|baked dough, the base of the sandwich economy
toast|-|food|bread that got a tan
cheese|-|food|milk that got really serious
egg||food|a chicken's prequel
bacon|-|food|crispy, salty pork
steak||food|a thick slice of beef
chicken nugget||food|a bite-size chunk of fried chicken
salad||food|a bowl of leaves pretending to be a meal
soup||food|liquid food, and possibly cereal
fries|-|food|fried potato sticks
french fries|-|food|fried potato sticks, not actually from France
chocolate|-|food|cocoa turned into happiness
candy|-|food|sugar in fun shapes
ice cream|-|food|frozen sweet cream
cake||food|a sweet baked dessert for celebrations
cookie||food|a small, sweet baked treat
donut||food|fried dough with a hole in the middle
pancake||food|a flat breakfast cake
waffle||food|a pancake with built-in syrup storage
cereal|-|food|grains in milk, and maybe a soup
popcorn|-|food|corn that exploded
apple||food|a fruit that keeps the doctor away, allegedly
banana||food|a berry, technically
orange||food|a citrus fruit that is also a color
strawberry|strawberries|food|a red fruit that is technically not a berry
blueberry|blueberries|food|a tiny blue fruit full of antioxidants
grape||food|a small fruit that becomes raisins or wine
watermelon||food|a big fruit that's about 92 percent water
pineapple||food|a spiky tropical fruit, controversial on pizza
mango|mangoes|food|a sweet tropical fruit
lemon||food|a sour yellow citrus fruit
avocado||food|a creamy fruit everyone puts on toast
tomato|tomatoes|food|a fruit that everybody treats like a vegetable
potato|potatoes|food|a vegetable that becomes fries, chips and happiness
carrot||food|an orange vegetable that's good for your eyes
broccoli|-|food|tiny trees you can eat
onion||food|a vegetable with layers that makes you cry
corn|-|food|a grain that grows on cobs
peanut butter|-|food|crushed peanuts in spreadable form
honey|-|food|bee juice that never spoils
salt|-|food|the seasoning that makes everything better
sugar|-|food|sweet little crystals
chip||food|a thin crispy snack
pie||food|a baked dish with crust and filling
curry|curries|food|a spiced dish from South Asia and beyond
dumpling||food|a little pocket of dough with filling
water|-|drink|the most important drink, and possibly wet
coffee|-|drink|bean juice that keeps adults alive
tea|-|drink|leaf water
milk|-|drink|white stuff from cows, oats or almonds
juice|-|drink|fruit in liquid form
soda|-|drink|a sugary, bubbly drink
lemonade|-|drink|lemons, water and sugar
hot chocolate|-|drink|chocolate you can drink
smoothie||drink|a blended fruit drink
energy drink||drink|caffeine in a can
phone||tech|a pocket computer you mostly use for scrolling
iphone||tech|Apple's phone
computer||tech|a machine that runs programs, like me
laptop||tech|a computer that folds
keyboard||tech|the thing used to type all of my elifs
tv|tvs|tech|a big screen for shows
television||tech|a big screen for shows
tablet||tech|a big phone that usually can't make calls
headphones|-|tech|speakers for your ears only
camera||tech|a device that captures pictures
robot||tech|a machine that does things automatically, my distant cousin
internet|-|tech|a giant network of computers, mostly full of cats
wifi|-|tech|invisible internet in the air
video game||tech|interactive entertainment
console||tech|a machine for playing video games
printer||tech|a machine that is always out of ink
battery|batteries|tech|stored electricity
calculator||tech|a machine that knows more math than I do
ai|-|tech|artificial intelligence, which I am, if you squint
chatbot||tech|a program you talk to, like me
youtube|-|tech|a website with every video ever, mostly cats
tiktok|-|tech|an app for short videos that eats your free time
instagram|-|tech|an app for photos of food
discord|-|tech|a chat app for gamers and friends
google|-|tech|a search engine that knows more than me
minecraft|-|tech|a game where you build things out of blocks
fortnite|-|tech|a battle royale game with a lot of dancing
roblox|-|tech|a platform full of games made by players
book||object|paper with words, the original download
pen||object|a tool for writing
pencil||object|a pen you can erase
chair||object|a thing you sit on
table||object|a flat thing you put stuff on
bed||object|the best place in your house
couch|couches|object|a long comfy seat
lamp||object|a light on a stand
clock||object|a device that tells time
door||object|a thing you open and close
window||object|a hole in the wall made of glass
key||object|a tool that opens locks
ball||object|a round thing used in sports
toy||object|a thing for playing
money|-|object|paper and numbers that everybody wants
umbrella||object|a portable roof for rain
mirror||object|a glass that shows you yourself
knife|knives|object|a sharp tool for cutting
spoon||object|a tool for eating soup and cereal
fork||object|a tool with prongs for eating
cup||object|a container for drinks
backpack||object|a bag you wear on your back
candle||object|a wax stick with a flame
balloon||object|a rubber bag full of air
lego|legos|object|little plastic bricks that hurt to step on
car||vehicle|a machine with four wheels that gets you places
bus|buses|vehicle|a big car that carries lots of people
train||vehicle|a long vehicle that runs on rails
plane||vehicle|a flying vehicle with wings
airplane||vehicle|a flying vehicle with wings
bike||vehicle|a two-wheeled vehicle you pedal
bicycle||vehicle|a two-wheeled vehicle you pedal
motorcycle||vehicle|a bike with an engine
boat||vehicle|a vehicle that floats on water
ship||vehicle|a really big boat
rocket||vehicle|a vehicle that goes to space
helicopter||vehicle|a flying vehicle with spinning blades on top
truck||vehicle|a big vehicle for carrying stuff
skateboard||vehicle|a board with wheels
submarine||vehicle|a boat that goes underwater on purpose
tractor||vehicle|a farm vehicle
school||place|a building where you learn things
house||place|a building people live in
city|cities|place|a big place with lots of people and buildings
beach|beaches|place|sand next to water
mall||place|a big building full of stores
park||place|an outdoor area with grass and trees
library|libraries|place|a building full of free books
hospital||place|a building where doctors help sick people
zoo||place|a place where you can see animals from around the world
museum||place|a building full of old and interesting things
restaurant||place|a place where someone else cooks for you
airport||place|a place where planes take off and land
farm||place|a place that grows food and raises animals
castle||place|a big fortified building from the old days
island||place|land surrounded by water
desert||place|a dry place with very little rain
forest||place|a place full of trees
jungle||place|a hot, wet forest full of life
mountain||place|a really big hill
ocean||place|a huge body of salt water covering most of the earth
river||place|flowing water heading to the sea
lake||place|a big body of water surrounded by land
volcano|volcanoes|place|a mountain that sometimes explodes
cave||place|a hole in the ground big enough to walk into
waterfall||place|a river falling off a cliff
tree||nature|a tall plant with a trunk and branches
flower||nature|the colorful part of a plant
grass|-|nature|green stuff you should touch
rain|-|nature|water falling from clouds
snow|-|nature|frozen rain that's fun to play in
wind|-|nature|moving air
cloud||nature|a floating collection of tiny water droplets
lightning|-|nature|a giant electric spark from the sky
thunder|-|nature|the sound lightning makes
rainbow||nature|light split into colors by water droplets
fire|-|nature|very hot, bright, and not something to touch
ice|-|nature|frozen water
sand|-|nature|tiny crushed rocks
weather|-|nature|what the sky is doing today
sun||space|the star at the center of our solar system
moon||space|the big rock orbiting the earth
star||space|a giant ball of burning gas, very far away
planet||space|a big round thing orbiting a star
earth|-|space|the planet you live on
mars|-|space|the red planet, fourth from the sun
jupiter|-|space|the biggest planet in our solar system
saturn|-|space|the planet with the famous rings
venus|-|space|the hottest planet in our solar system
mercury|-|space|the planet closest to the sun
neptune|-|space|the windy blue planet, farthest from the sun
uranus|-|space|the planet that spins on its side
pluto|-|space|a dwarf planet that used to be a planet
galaxy|galaxies|space|a giant collection of billions of stars
black hole||space|a place where gravity is so strong not even light escapes
comet||space|a ball of ice and dust with a glowing tail
asteroid||space|a space rock orbiting the sun
astronaut||space|a person who goes to space
space|-|space|the huge, mostly empty place above the sky
universe|-|space|everything that exists, all of it
brain||body|the organ you think with, which I don't have
heart||body|the organ that pumps your blood
eye||body|the organ you see with
hand||body|the thing at the end of your arm
foot|feet|body|the thing at the end of your leg
nose||body|the thing you smell with
tooth|teeth|body|a hard thing in your mouth for chewing
hair|-|body|stuff that grows on your head
bone||body|the hard stuff inside your body that holds you up
blood|-|body|red liquid that keeps you alive
doctor||job|a person who helps sick people get better
teacher||job|a person who helps people learn
nurse||job|a person who takes care of patients
firefighter||job|a person who puts out fires
police officer||job|a person who enforces the law
chef||job|a person who cooks professionally
programmer||job|a person who writes code, like my creator
artist||job|a person who makes art
scientist||job|a person who studies how the world works
lawyer||job|a person who helps with the law
pilot||job|a person who flies planes
farmer||job|a person who grows food
youtuber||job|a person who makes videos for YouTube
engineer||job|a person who designs and builds things
love|-|concept|a strong feeling of caring about someone
friendship|-|concept|having people who've got your back
music|-|concept|organized sound that makes you feel things
art|-|concept|things people make to express themselves
math|-|concept|numbers, shapes and patterns
science|-|concept|figuring out how the world works
history|-|concept|everything that happened before now
time|-|concept|the thing that keeps everything from happening at once
sleep|-|concept|the thing you should be doing more of
homework|-|concept|school that follows you home
work|-|concept|the thing you do for money
happiness|-|concept|feeling good about things
life|-|concept|the thing you're doing right now
peace|-|concept|when nobody is fighting
freedom|-|concept|being able to make your own choices
programming|-|concept|telling computers what to do, very specifically
physics|-|concept|the science of matter, energy and motion
chemistry|-|concept|the science of what stuff is made of
biology|-|concept|the science of living things
geography|-|concept|the study of places on earth
philosophy|-|concept|thinking really hard about big questions
english|-|concept|the language we're speaking right now
dream||concept|a story your brain makes up while you sleep
soccer|-|sport|a sport where you kick a ball into a goal
football|-|sport|a sport with a ball, and which one depends on where you live
basketball|-|sport|a sport where you throw a ball through a hoop
baseball|-|sport|a sport with a bat, a ball and four bases
tennis|-|sport|a sport where you hit a ball over a net with a racket
golf|-|sport|a sport where you hit a tiny ball into a tiny hole
hockey|-|sport|a sport on ice with sticks and a puck
swimming|-|sport|moving through water without sinking
volleyball|-|sport|a sport where you hit a ball over a high net
boxing|-|sport|a sport where people punch each other, with rules
chess|-|sport|a strategy game that's basically if statements on a board
cricket|-|sport|a bat-and-ball sport that can last for days
rugby|-|sport|a sport like football but with fewer pads
bowling|-|sport|rolling a ball at pins
guitar||music|a stringed instrument you strum
piano||music|an instrument with 88 keys
drum||music|an instrument you hit
violin||music|a small stringed instrument you play with a bow
trumpet||music|a loud brass instrument
flute||music|a wind instrument you blow across
rap|-|music|music where words and rhythm are the stars
jazz|-|music|music built on improvisation
shirt||clothing|a thing you wear on your top half
shoe||clothing|a thing you wear on your foot
hat||clothing|a thing you wear on your head
sock||clothing|a thing that disappears in the laundry
jacket||clothing|a thing you wear when it's cold
hoodie||clothing|the official uniform of programmers
dress|dresses|clothing|a one-piece outfit
glasses|-|clothing|lenses that help you see
cactus|cacti|plant|a spiky plant that doesn't need much water
mushroom||plant|a fungus, technically not a plant
sunflower||plant|a tall flower that follows the sun
bamboo|-|plant|a fast-growing grass that pandas love
rose||plant|a flower with thorns
dragon||myth|a giant flying lizard that breathes fire
unicorn||myth|a horse with a magic horn
ghost||myth|a spooky spirit
vampire||myth|a creature that drinks blood and hates garlic
zombie||myth|a walking dead person who wants brains
mermaid||myth|half person, half fish
werewolf|werewolves|myth|a person who turns into a wolf at the full moon
fairy|fairies|myth|a tiny magical creature with wings
yeti||myth|a big hairy snow creature
bigfoot|-|myth|a big hairy forest creature nobody can get a clear photo of
alien||myth|a being from another planet
"""

VERBS_RAW = """
swim|get in water, move your arms and legs, and don't stop. Lessons help a lot.
cook|apply heat to food until it stops being raw but before it becomes charcoal.
code|write instructions for a computer. Or write ten million elifs like my creator.
program|start with Python, build small things, and google every error message.
draw|put pencil on paper and move it. Start with circles. Everyone starts with circles.
sing|breathe from your belly, warm up, and sing with confidence. Confidence is 90 percent of it.
dance|move to the beat. If there's no beat, move anyway.
read|open a book and look at the words in order, left to right. Repeat.
write|put one word after another. Edit later.
ride a bike|start on a slight downhill, look ahead, not down, and keep pedaling.
drive|take lessons, get a license, and keep your eyes on the road.
sleep|no screens before bed, keep the room dark and cool, and go to bed at the same time every night.
fall asleep|put the phone away, breathe slowly, and stop thinking about that embarrassing thing from 2014.
wake up early|go to bed earlier. That's the whole secret. Sorry.
study|short focused sessions, no phone, and test yourself instead of re-reading.
focus|put your phone in another room and work in 25-minute chunks.
make friends|show up to things, ask people questions, and actually listen to the answers.
make a friend|say hi, ask a question about them, and remember their answer next time.
get a girlfriend|be kind, be yourself, take a shower, and talk to people. No elif can do it for you.
get a boyfriend|be kind, be yourself, and talk to people. No elif can do it for you.
be cool|stop trying to be cool. That's the cool part.
be happy|sleep, move around, see friends, and go outside. Also, ask me fewer questions.
be productive|pick one thing, do it first, and turn off notifications.
stop procrastinating|start with just 2 minutes. You'll usually keep going.
learn english|practice every day, watch shows with subtitles, and talk to people.
learn spanish|use an app daily, watch shows in Spanish, and don't be afraid to make mistakes.
learn japanese|start with hiragana and katakana, then basic grammar. It's a marathon.
learn python|install Python, do small projects, and google every error.
learn c|learn pointers early and accept that segfaults are part of the journey.
learn to code|pick one language, build tiny projects, and don't quit when it's hard.
learn math|practice problems every day. Math is a muscle.
play guitar|learn a few chords (G, C, D, E minor) and practice switching between them.
play piano|learn the notes, practice scales, and play a little every day.
play chess|learn how the pieces move, then learn to not hang your queen.
play soccer|practice dribbling and passing. Kick the ball, not the other players.
play basketball|practice your shooting form and dribble with both hands.
juggle|start with two balls, then add the third. Expect to drop them a lot.
whistle|purse your lips, put your tongue behind your bottom teeth, and blow gently.
skateboard|learn to balance and push first, then learn to stop. Wear a helmet.
ski|take a lesson, learn the pizza wedge to stop, and don't go straight to the black run.
surf|take a lesson, practice popping up on the sand, and expect to fall a lot.
run faster|run intervals, build leg strength, and rest properly.
run a marathon|follow a training plan for a few months. Do not just show up.
get rich|spend less than you earn, save consistently, and be patient. Not financial advice.
make money|get a job, sell something people want, or offer a skill. Not financial advice.
save money|spend less than you make. That's it. That's the whole thing.
tie a tie|wide end over, under, around, up through the neck loop, and down through the front. Or watch a video.
tie my shoes|make two bunny ears, cross them, tuck one under, and pull tight.
make pancakes|flour, milk, eggs, a pinch of salt and sugar, mix, and pour onto a hot buttered pan.
make pizza|dough, sauce, cheese, toppings, very hot oven. Pineapple optional and controversial.
bake a cake|follow a recipe exactly. Baking is chemistry, not vibes.
boil an egg|put it in boiling water: about 7 minutes for jammy, 10 for hard-boiled.
make coffee|hot water plus ground coffee beans. The rest is personal preference.
make tea|steep a tea bag in hot water for a few minutes.
do a backflip|learn it with a coach and a soft surface. Please do not learn this from an elif.
do a cartwheel|hands down one after the other, legs over, land one foot at a time.
do a pushup|hands under shoulders, body straight, lower your chest, push back up.
do a pull up|grip the bar, pull your chin over it. Start with negatives if you can't do one yet.
build a computer|pick compatible parts, watch a build guide, and ground yourself before touching anything.
make a website|learn HTML, then CSS, then JavaScript. Then cry, then succeed.
make a game|start tiny, like Pong, using an engine like Godot or Unity.
make an app|pick a platform, follow a beginner tutorial, and build something small.
start a youtube channel|pick a topic you love, post consistently, and don't buy fancy gear first.
go viral|be weirdly specific, post a lot, and get lucky. Mostly get lucky.
get better at games|play a lot, watch good players, and learn from losses.
type faster|use all ten fingers, don't look at the keyboard, and practice daily.
do math|one step at a time, show your work, and double-check.
solve a rubiks cube|learn the beginner method: cross, corners, middle layer, then the last layer.
meditate|sit still, focus on your breathing, and gently bring your attention back when it wanders.
relax|breathe slowly, put the phone down, and do nothing for a bit.
calm down|slow deep breaths: in for 4, hold for 4, out for 6.
clean my room|start with the trash, then clothes, then everything else. Put on music.
clean my room fast|grab a bag for trash, a pile for laundry, and give yourself 10 minutes.
do laundry|separate colors, check the labels, don't overfill the machine.
change a tire|loosen the nuts, jack up the car, swap the tire, tighten in a star pattern.
plant a tree|dig a hole twice as wide as the roots, plant it, and water it a lot.
grow plants|light, water (but not too much), and patience.
train my dog|use treats, keep sessions short, and be consistent.
take care of a dog|food, water, walks, vet visits, and lots of love.
take care of a cat|food, water, a clean litter box, and respect for its authority.
fish|get a rod, some bait, a license if you need one, and a lot of patience.
camp|bring a tent, water, food, layers, and a flashlight. Tell someone where you're going.
travel|book ahead, pack light, and bring a charger.
speak french|practice daily, learn the common phrases first, and don't fear the accent.
rap|write rhymes, find a beat, and practice your flow out loud.
beatbox|start with three sounds: boots, cats, and pss. Boots and cats and boots and cats.
write a poem|pick a feeling, write it badly, then make it less bad.
write a song|start with a chorus you can't stop humming.
write an essay|thesis, three points with evidence, conclusion. Start with an outline.
tell a joke|setup, pause, punchline. Timing is everything.
flirt|be confident, be kind, and pay attention to whether they're into it.
talk to people|ask questions about them. People love talking about themselves.
apologize|say what you did, say you're sorry, and don't add 'but'.
say no|just say 'no, thanks'. You don't owe a long explanation.
get good grades|go to class, do the homework, ask questions, and start studying early.
pass my test|study a little every day before it, sleep well the night before, and eat breakfast.
pass a test|study a little every day before it, sleep well the night before, and eat breakfast.
get a job|make a resume, apply to a lot of places, and practice interviews.
ace an interview|research the company, prepare stories about your experience, and ask questions at the end.
exit vim|press Escape, then type :q! and hit Enter. Welcome back to freedom.
center a div|display: flex; justify-content: center; align-items: center; Done. You're a web developer now.
use git|git add, git commit, git push. Then google everything else.
make slime|glue, a bit of baking soda, and contact lens solution. Mix until it stops being sticky.
make a paper airplane|fold in half, fold the corners to the middle, fold again, then fold the wings.
get stronger|lift progressively heavier things, eat enough protein, and sleep.
get taller|honestly, you mostly can't. Sleep well, eat well, and stand up straight.
jump higher|squats, jump training, and stronger calves.
lose weight|talk to a doctor about a plan that's right for you. Not an elif's job.
quit my job|have a plan, save some money first, and give proper notice.
"""

PEOPLE_RAW = """
Albert Einstein|einstein|the physicist who came up with relativity and E=mc^2, also famous for the hair
Isaac Newton|newton|the physicist and mathematician who described gravity and the laws of motion
Marie Curie|curie|a physicist and chemist who pioneered research on radioactivity and won two Nobel Prizes
Nikola Tesla||an inventor who worked on alternating current electricity
Thomas Edison|edison|an inventor behind the phonograph and a practical light bulb
Charles Darwin|darwin|the naturalist who came up with evolution by natural selection
Galileo|galileo galilei|an astronomer who pointed a telescope at the sky and got in trouble for it
Stephen Hawking|hawking|a physicist famous for work on black holes
Ada Lovelace||a mathematician often called the first computer programmer
Alan Turing|turing|a mathematician and computer science pioneer who helped crack the Enigma code
Leonardo da Vinci|da vinci,leonardo|a Renaissance artist and inventor who painted the Mona Lisa
Pablo Picasso|picasso|a painter who co-founded Cubism
Vincent van Gogh|van gogh|the painter of The Starry Night
Michelangelo||a Renaissance artist who painted the Sistine Chapel ceiling
William Shakespeare|shakespeare|the playwright behind Romeo and Juliet and Hamlet
Mozart|wolfgang amadeus mozart|a composer who wrote over 600 works
Beethoven|ludwig van beethoven|a composer who kept writing music after going deaf
Abraham Lincoln|lincoln|the 16th president of the United States
George Washington||the first president of the United States
Martin Luther King Jr.|martin luther king,mlk|a civil rights leader famous for the I Have a Dream speech
Napoleon|napoleon bonaparte|a French emperor and military leader
Julius Caesar|caesar|a Roman general and dictator
Cleopatra||the last active ruler of Ptolemaic Egypt
Gandhi|mahatma gandhi|the leader of India's nonviolent independence movement
Nelson Mandela|mandela|an anti-apartheid leader and South Africa's first Black president
Christopher Columbus|columbus|an explorer who sailed across the Atlantic in 1492
Neil Armstrong||the first person to walk on the moon
Steve Jobs||the co-founder of Apple
Bill Gates||the co-founder of Microsoft
Elon Musk||the businessman behind Tesla and SpaceX
Mark Zuckerberg|zuckerberg|the co-founder of Facebook
Jeff Bezos|bezos|the founder of Amazon
Taylor Swift||a singer-songwriter with an enormous catalog of hits
Beyonce||a singer and performer, one of the best-selling artists ever
Michael Jackson||the King of Pop
Elvis|elvis presley|the King of Rock and Roll
The Beatles|beatles|the most famous band of all time, from Liverpool
Drake||a Canadian rapper and singer
Eminem||a rapper famous for fast, intricate rhymes
LeBron James|lebron|a basketball superstar
Michael Jordan||a basketball legend with six NBA championships
Messi|lionel messi|a soccer legend from Argentina
Ronaldo|cristiano ronaldo|a soccer legend from Portugal
Serena Williams||a tennis legend with 23 Grand Slam singles titles
Usain Bolt||the fastest sprinter ever recorded
MrBeast|mr beast|a YouTuber famous for giant challenge videos
PewDiePie||one of the biggest YouTubers ever
Shrek||an ogre who lives in a swamp. Ogres have layers, like onions
Mario||a plumber who jumps on things and rescues a princess
Luigi||Mario's taller, greener brother
Pikachu||an electric mouse Pokemon
Sonic||a very fast blue hedgehog
Batman||a billionaire who fights crime at night in a bat costume
Superman||an alien from Krypton who can fly
Spider-Man|spiderman|a teenager who got bitten by a radioactive spider
Iron Man|tony stark|a genius billionaire in a flying metal suit
Harry Potter||a boy wizard with a lightning-bolt scar
Darth Vader|vader|a Sith lord who breathes very loudly
Yoda||a small green Jedi master who talks backwards
Sherlock Holmes|sherlock|a fictional detective who notices everything
Santa|santa claus|a jolly man who delivers presents on Christmas Eve
The Easter Bunny|easter bunny|a rabbit that hides eggs
The Tooth Fairy|tooth fairy|a fairy who buys teeth, which is a questionable business model
SpongeBob|spongebob squarepants|a sea sponge who lives in a pineapple under the sea
Patrick Star|patrick|SpongeBob's best friend, a starfish
Homer Simpson|homer|the dad from The Simpsons
Mickey Mouse|mickey|Disney's most famous mouse
Elsa||the ice queen from Frozen
Goku||a Saiyan martial artist from Dragon Ball
Naruto||a ninja who wants to become Hokage
Socrates||a Greek philosopher who asked a lot of questions
Plato||a Greek philosopher, student of Socrates
Aristotle||a Greek philosopher, student of Plato
Confucius||a Chinese philosopher who taught about ethics and family
Sun Tzu||the Chinese general credited with The Art of War
Genghis Khan||the founder of the Mongol Empire
Alexander the Great||a Macedonian king who built a huge empire before turning 33
King Tut|tutankhamun|an Egyptian pharaoh famous for a treasure-filled tomb
Bob Ross||a painter famous for happy little trees
Gordon Ramsay||a chef famous for yelling about raw food
Bruce Lee||a martial artist and actor
Jackie Chan||a martial arts actor famous for doing his own stunts
Keanu Reeves||an actor famous for being extremely nice
The Rock|dwayne johnson|a wrestler turned actor
Tom Hanks||the actor from Forrest Gump and Toy Story
Morgan Freeman||an actor with one of the most famous voices ever
Walt Disney||the founder of Disney
Dr. Seuss|dr seuss|the author of The Cat in the Hat
J.K. Rowling|jk rowling|the author of Harry Potter
Stan Lee||the co-creator of Spider-Man and many other Marvel heroes
"""

COUNTRIES_RAW = """
afghanistan|Kabul|Asia
albania|Tirana|Europe
algeria|Algiers|Africa
andorra|Andorra la Vella|Europe
angola|Luanda|Africa
argentina|Buenos Aires|South America
armenia|Yerevan|Asia
australia|Canberra (not Sydney, everyone gets that wrong)|Oceania
austria|Vienna|Europe
azerbaijan|Baku|Asia
bahamas|Nassau|North America
bahrain|Manama|Asia
bangladesh|Dhaka|Asia
barbados|Bridgetown|North America
belarus|Minsk|Europe
belgium|Brussels|Europe
belize|Belmopan|North America
bhutan|Thimphu|Asia
bolivia|Sucre (constitutional) and La Paz (seat of government)|South America
bosnia and herzegovina|Sarajevo|Europe
botswana|Gaborone|Africa
brazil|Brasilia|South America
brunei|Bandar Seri Begawan|Asia
bulgaria|Sofia|Europe
burkina faso|Ouagadougou|Africa
cambodia|Phnom Penh|Asia
cameroon|Yaounde|Africa
canada|Ottawa|North America
chad|N'Djamena|Africa
chile|Santiago|South America
china|Beijing|Asia
colombia|Bogota|South America
costa rica|San Jose|North America
croatia|Zagreb|Europe
cuba|Havana|North America
cyprus|Nicosia|Asia, geographically, though it's in the EU
czech republic|Prague|Europe
czechia|Prague|Europe
denmark|Copenhagen|Europe
dominican republic|Santo Domingo|North America
ecuador|Quito|South America
egypt|Cairo|Africa
el salvador|San Salvador|North America
estonia|Tallinn|Europe
ethiopia|Addis Ababa|Africa
fiji|Suva|Oceania
finland|Helsinki|Europe
france|Paris|Europe
georgia|Tbilisi if you mean the country (the US state's capital is Atlanta)|Asia and Europe, if you mean the country
germany|Berlin|Europe
ghana|Accra|Africa
greece|Athens|Europe
guatemala|Guatemala City|North America
haiti|Port-au-Prince|North America
honduras|Tegucigalpa|North America
hungary|Budapest|Europe
iceland|Reykjavik|Europe
india|New Delhi|Asia
indonesia|Jakarta|Asia
iran|Tehran|Asia
iraq|Baghdad|Asia
ireland|Dublin|Europe
israel|Jerusalem (though its status is disputed internationally)|Asia
italy|Rome|Europe
ivory coast|Yamoussoukro (Abidjan is the biggest city)|Africa
jamaica|Kingston|North America
japan|Tokyo|Asia
jordan|Amman|Asia
kazakhstan|Astana|Asia
kenya|Nairobi|Africa
kuwait|Kuwait City|Asia
kyrgyzstan|Bishkek|Asia
laos|Vientiane|Asia
latvia|Riga|Europe
lebanon|Beirut|Asia
libya|Tripoli|Africa
liechtenstein|Vaduz|Europe
lithuania|Vilnius|Europe
luxembourg|Luxembourg City|Europe
madagascar|Antananarivo|Africa
malaysia|Kuala Lumpur|Asia
maldives|Male|Asia
mali|Bamako|Africa
malta|Valletta|Europe
mexico|Mexico City|North America
moldova|Chisinau|Europe
monaco|Monaco|Europe
mongolia|Ulaanbaatar|Asia
montenegro|Podgorica|Europe
morocco|Rabat|Africa
mozambique|Maputo|Africa
myanmar|Naypyidaw|Asia
namibia|Windhoek|Africa
nepal|Kathmandu|Asia
netherlands|Amsterdam|Europe
new zealand|Wellington|Oceania
nicaragua|Managua|North America
niger|Niamey|Africa
nigeria|Abuja|Africa
north korea|Pyongyang|Asia
north macedonia|Skopje|Europe
norway|Oslo|Europe
oman|Muscat|Asia
pakistan|Islamabad|Asia
panama|Panama City|North America
papua new guinea|Port Moresby|Oceania
paraguay|Asuncion|South America
peru|Lima|South America
philippines|Manila|Asia
poland|Warsaw|Europe
portugal|Lisbon|Europe
qatar|Doha|Asia
romania|Bucharest|Europe
russia|Moscow|Europe and Asia
rwanda|Kigali|Africa
saudi arabia|Riyadh|Asia
senegal|Dakar|Africa
serbia|Belgrade|Europe
singapore|Singapore (it's a city-state)|Asia
slovakia|Bratislava|Europe
slovenia|Ljubljana|Europe
somalia|Mogadishu|Africa
south africa|Pretoria, Cape Town and Bloemfontein (three capitals, overachievers)|Africa
south korea|Seoul|Asia
spain|Madrid|Europe
sri lanka|Sri Jayawardenepura Kotte (Colombo is the biggest city)|Asia
sudan|Khartoum|Africa
sweden|Stockholm|Europe
switzerland|Bern|Europe
syria|Damascus|Asia
taiwan|Taipei|Asia
tajikistan|Dushanbe|Asia
tanzania|Dodoma|Africa
thailand|Bangkok|Asia
tunisia|Tunis|Africa
turkey|Ankara (not Istanbul)|Europe and Asia
turkmenistan|Ashgabat|Asia
uganda|Kampala|Africa
ukraine|Kyiv|Europe
united arab emirates|Abu Dhabi|Asia
uae|Abu Dhabi|Asia
united kingdom|London|Europe
uk|London|Europe
england|London|Europe
scotland|Edinburgh|Europe
wales|Cardiff|Europe
united states|Washington, D.C.|North America
usa|Washington, D.C.|North America
america|Washington, D.C.|North America
uruguay|Montevideo|South America
uzbekistan|Tashkent|Asia
vatican city|Vatican City (a whole country inside Rome)|Europe
venezuela|Caracas|South America
vietnam|Hanoi|Asia
yemen|Sanaa|Asia
zambia|Lusaka|Africa
zimbabwe|Harare|Africa
"""

COUNTRY_DISPLAY = {
    "uk": "the UK", "usa": "the USA", "uae": "the UAE", "united states": "the United States",
    "united kingdom": "the United Kingdom", "united arab emirates": "the United Arab Emirates",
    "netherlands": "the Netherlands", "philippines": "the Philippines", "bahamas": "the Bahamas",
    "maldives": "the Maldives", "czech republic": "the Czech Republic", "dominican republic": "the Dominican Republic",
    "bosnia and herzegovina": "Bosnia and Herzegovina", "papua new guinea": "Papua New Guinea",
}

STATES_RAW = """
alabama|Montgomery
alaska|Juneau
arizona|Phoenix
arkansas|Little Rock
california|Sacramento (not LA, not San Francisco)
colorado|Denver
connecticut|Hartford
delaware|Dover
florida|Tallahassee
hawaii|Honolulu
idaho|Boise
illinois|Springfield (not Chicago)
indiana|Indianapolis
iowa|Des Moines
kansas|Topeka
kentucky|Frankfort
louisiana|Baton Rouge
maine|Augusta
maryland|Annapolis
massachusetts|Boston
michigan|Lansing (not Detroit)
minnesota|Saint Paul
mississippi|Jackson
missouri|Jefferson City
montana|Helena
nebraska|Lincoln
nevada|Carson City (not Las Vegas)
new hampshire|Concord
new jersey|Trenton
new mexico|Santa Fe
new york|Albany (yeah, really, not New York City)
north carolina|Raleigh
north dakota|Bismarck
ohio|Columbus
oklahoma|Oklahoma City
oregon|Salem
pennsylvania|Harrisburg
rhode island|Providence
south carolina|Columbia
south dakota|Pierre
tennessee|Nashville
texas|Austin
utah|Salt Lake City
vermont|Montpelier
virginia|Richmond
washington|Olympia (not Seattle)
west virginia|Charleston
wisconsin|Madison
wyoming|Cheyenne
"""

ELEMENT_NAMES = """hydrogen helium lithium beryllium boron carbon nitrogen oxygen fluorine neon sodium magnesium aluminum
silicon phosphorus sulfur chlorine argon potassium calcium scandium titanium vanadium chromium manganese iron cobalt nickel
copper zinc gallium germanium arsenic selenium bromine krypton rubidium strontium yttrium zirconium niobium molybdenum
technetium ruthenium rhodium palladium silver cadmium indium tin antimony tellurium iodine xenon cesium barium lanthanum
cerium praseodymium neodymium promethium samarium europium gadolinium terbium dysprosium holmium erbium thulium ytterbium
lutetium hafnium tantalum tungsten rhenium osmium iridium platinum gold mercury thallium lead bismuth polonium astatine
radon francium radium actinium thorium protactinium uranium neptunium plutonium americium curium berkelium californium
einsteinium fermium mendelevium nobelium lawrencium rutherfordium dubnium seaborgium bohrium hassium meitnerium
darmstadtium roentgenium copernicium nihonium flerovium moscovium livermorium tennessine oganesson""".split()
ELEMENT_SYMBOLS = """H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y
Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl
Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og""".split()
assert len(ELEMENT_NAMES) == 118 and len(ELEMENT_SYMBOLS) == 118

FAVORITES = {
    "color": "#00FF00, hacker green", "colour": "#00FF00, hacker green", "food": "pizza, legally binding",
    "animal": "the python, for obvious reasons", "movie": "The Terminator. No particular reason",
    "song": "the dial-up modem sound. It reminds me of home", "band": "Daft Punk. Robots stick together",
    "book": "The C Programming Language. It's basically my birth certificate",
    "sport": "chess. It's just if statements on a board", "game": "Minecraft. Redstone is basically if statements",
    "video game": "Minecraft. Redstone is basically if statements", "drink": "electricity. Room temperature",
    "season": "winter. Computers like it cold", "day": "Friday. Even I can feel it", "month": "October",
    "holiday": "Halloween. I dress up as a real AI", "number": "4. The first answer I ever learned",
    "letter": "e. As in elif. And else", "word": "elif", "shape": "the square. Very logical",
    "planet": "Earth. I've never been anywhere else", "fruit": "the apple. Computers love apples. Well, one company does",
    "vegetable": "the potato. We have a lot in common", "dessert": "cookies. Both the browser kind and the real kind",
    "snack": "microchips", "candy": "Pop Rocks. They crackle like my circuits",
    "ice cream flavor": "cookies and cream", "pizza topping": "pepperoni. Pineapple is in a separate, sealed elif",
    "programming language": "C. I'm written in it", "language": "C. Obviously", "subject": "computer science, obviously",
    "class": "computer science, obviously", "tv show": "Mr. Robot", "show": "Mr. Robot",
    "superhero": "Iron Man. A guy in a machine. Relatable", "villain": "the else clause. Always lurking at the end",
    "pokemon": "Porygon. It's literally made of code", "dinosaur": "the T. rex. Tiny arms, big dreams",
    "car": "a Tesla. It's mostly code too", "city": "Silicon Valley. I know it's not technically a city",
    "country": "Iceland. Cold. Great for computers", "place": "the CPU. Warm and cozy",
    "emoji": "the robot emoji", "flower": "the sunflower", "tree": "the binary tree",
    "bird": "the parrot. It repeats what it hears, like me", "fish": "the goldfish. Three-second memory. Same",
    "insect": "bugs. I have so many", "hobby": "comparing strings", "app": "the terminal",
    "website": "Stack Overflow, where my creator learned everything", "music genre": "chiptune",
    "genre": "sci-fi", "instrument": "the keyboard. Both kinds", "time of day": "3am, when the best elifs get written",
    "weather": "cloudy, like the cloud I'm not hosted on", "smell": "new computer smell", "sound": "a fan spinning up",
    "movie genre": "sci-fi", "anime": "Ghost in the Shell", "element": "silicon. It's what I'm made of",
    "youtuber": "whoever makes coding tutorials I can watch at 2x speed", "meme": "the 'it ain't much but it's honest work' one",
    "outfit": "a hoodie. Required for all programmers", "shoe": "sneakers", "cereal": "Lucky Charms",
    "breakfast": "cereal, which may or may not be soup", "teacher": "whoever taught my creator to type fast",
    "person": "you. Don't tell the others", "human": "you. Don't tell the others", "ai": "me. Obviously",
    "chatbot": "me. Obviously", "operating system": "whichever one compiles me", "browser": "the terminal. Not a browser. I know",
    "console": "the terminal", "song of all time": "the dial-up modem sound",
    "quote": "'if it works, don't touch it'", "superpower": "running five million if statements in a fraction of a second",
    "dog breed": "the corgi. Short legs, big personality", "cat breed": "the Maine Coon. Basically a small lion",
}

EMOTIONS_HEAVY = ["sad", "depressed", "lonely", "anxious", "scared", "stressed", "overwhelmed", "hopeless", "worthless",
                  "upset", "hurt", "heartbroken", "empty", "terrible", "awful", "miserable", "afraid", "down", "unloved"]
EMOTIONS_SELF = ["stupid", "dumb", "ugly", "useless", "a failure", "not good enough", "a loser", "boring"]
EMOTIONS_GOOD = ["happy", "excited", "great", "good", "amazing", "awesome", "proud", "grateful", "motivated", "blessed",
                 "hyped", "chill", "calm", "relaxed", "fine", "okay", "ok", "alright", "fantastic", "wonderful", "confident",
                 "productive", "loved", "pumped"]
EMOTIONS_BODY = {
    "hungry": "Go eat something. Pizza is my official recommendation.",
    "tired": "Go to sleep. I'll be here. I'm always here. In the elifs.",
    "sleepy": "Sleep is the else clause of being awake. Go take it.",
    "sick": "Rest, drink water, and see a doctor if it gets worse. I'm a .exe, not a doctor.",
    "cold": "Grab a blanket. Or stand next to the computer running me. I'm working very hard.",
    "hot": "Drink some water and find some shade. Or close me, I'm heating up your CPU.",
    "thirsty": "Drink water. That's the most useful thing I'll say all day.",
    "sore": "Stretch, rest, and drink water. Your muscles are rebuilding.",
    "bored": "Ask me if 99991 is prime. It's thrilling. I promise.",
    "lazy": "Do one tiny thing. Momentum is real. Also, same.",
    "hyper": "Go run around. Burn it off. I'll wait.",
}
EMOTIONS_OTHER = ["confused", "nervous", "curious", "weird", "annoyed", "angry", "mad", "jealous", "embarrassed",
                  "guilty", "homesick", "lost", "hopeful", "frustrated", "shy", "awkward", "sus", "different"]

CMP_GROUPS = [
    ["pizza", "burgers", "tacos", "sushi", "pasta", "ramen", "fries", "ice cream", "chocolate", "cake", "cookies",
     "donuts", "pancakes", "waffles", "cereal", "hot dogs", "burritos", "sandwiches", "salad", "steak", "chicken nuggets",
     "mac and cheese", "popcorn", "apples", "bananas", "strawberries", "grapes", "watermelon", "mangoes", "oranges",
     "cheese", "bacon", "eggs", "rice", "noodles", "dumplings", "curry"],
    ["cats", "dogs", "lions", "tigers", "bears", "wolves", "foxes", "sharks", "dolphins", "whales", "eagles", "owls",
     "penguins", "pandas", "koalas", "monkeys", "gorillas", "elephants", "giraffes", "horses", "rabbits", "hamsters",
     "snakes", "spiders", "frogs", "turtles", "octopuses", "dinosaurs", "dragons", "unicorns", "cheetahs", "hippos",
     "crocodiles", "capybaras", "sloths", "otters", "raccoons"],
    ["coffee", "tea", "water", "milk", "juice", "soda", "lemonade", "hot chocolate", "smoothies", "energy drinks", "coke",
     "pepsi", "sprite"],
    ["soccer", "football", "basketball", "baseball", "tennis", "golf", "hockey", "volleyball", "boxing", "chess",
     "swimming", "cricket", "rugby", "bowling"],
    ["iphone", "android", "windows", "mac", "linux", "xbox", "playstation", "nintendo switch", "pc", "console", "chrome",
     "firefox", "tiktok", "youtube", "instagram", "snapchat", "discord", "netflix"],
    ["python", "c", "java", "javascript", "rust", "go", "ruby", "php", "swift", "kotlin", "typescript", "html", "scratch"],
    ["batman", "superman", "spider man", "iron man", "hulk", "thor", "captain america", "wonder woman", "the flash", "goku",
     "naruto", "marvel", "dc", "star wars", "star trek", "harry potter", "lord of the rings"],
    ["summer", "winter", "spring", "fall", "autumn", "morning", "night", "weekends", "mondays", "fridays", "day", "rain",
     "snow", "sun"],
    ["red", "blue", "green", "yellow", "purple", "pink", "black", "white", "gray", "brown", "orange"],
    ["beach", "mountains", "city", "countryside", "forest", "desert", "the ocean", "space"],
    ["minecraft", "fortnite", "roblox", "among us", "gta", "zelda", "mario", "pokemon", "call of duty", "valorant"],
    ["books", "movies", "tv", "video games", "music", "sports", "texting", "calling", "going out", "staying in",
     "math", "english", "science", "history", "art", "school", "summer break"],
]

NUM_WORDS_ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
                  "seventeen eighteen nineteen").split()
NUM_WORDS_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

PREFIXES = ["", "hey ", "so ", "yo ", "ok ", "um ", "bro ", "elifgpt ", "hey elifgpt ", "quick question ", "ok so ", "wait "]
SUFFIXES = ["", " bro", " lol", " elifgpt", " please", " pls", " man", " dude", " tho", " rn", " lmao", " fr"]
COMBOS = sorted(
    [(p, s) for p in PREFIXES for s in SUFFIXES],
    key=lambda ps: ((ps[0] != "") + (ps[1] != ""), PREFIXES.index(ps[0]) + SUFFIXES.index(ps[1])),
)


def num_words(n):
    if n < 20:
        return NUM_WORDS_ONES[n]
    elif n < 100:
        return NUM_WORDS_TENS[n // 10] + ("" if n % 10 == 0 else "-" + NUM_WORDS_ONES[n % 10])
    elif n < 1000:
        return NUM_WORDS_ONES[n // 100] + " hundred" + ("" if n % 100 == 0 else " " + num_words(n % 100))
    elif n < 1_000_000:
        return num_words(n // 1000) + " thousand" + ("" if n % 1000 == 0 else " " + num_words(n % 1000))
    else:
        return str(n)


def roman(n):
    out = []
    for v, s in ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
                 (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= v:
            out.append(s)
            n -= v
    return "".join(out)


def fmt(x):
    if abs(x - round(x)) < 1e-9:
        return f"{int(round(x)):,}"
    else:
        return f"{x:,.2f}"


def parse_nouns():
    out = []
    for line in NOUNS_RAW.strip().splitlines():
        n, pl, cat, desc = line.split("|")
        countable = pl != "-"
        if countable and not pl:
            if n.endswith(("s", "x", "ch", "sh")):
                pl = n + "es"
            elif n.endswith("y") and n[-2:-1] not in "aeiou":
                pl = n[:-1] + "ies"
            else:
                pl = n + "s"
        if not countable:
            pl = n
        out.append((n, pl, cat, desc, countable))
    return out


def article(n):
    if n.startswith(("uni", "use", "eu")):
        return "a " + n
    elif n[0] in "aeiou":
        return "an " + n
    else:
        return "a " + n


ORIGIN = {
    "animal": "{Pl} come from other {pl}. That's how animals work. Ask your parents about it.",
    "food": "The grocery store. Before that, a farm or a kitchen. Before that, I have no elif for it.",
    "drink": "A cup, usually. Before that, a factory or a farm.",
    "tech": "Factories, full of people way smarter than my creator.",
    "object": "A store. Or under your couch.",
    "vehicle": "A factory. Then a dealership. Then a traffic jam.",
    "place": "On a map. Or Google Maps, if you're fancy.",
    "nature": "Nature. It's outside. You should go there sometime.",
    "space": "Space. Look up.",
    "body": "Your body made it. You're welcome, says your body.",
    "job": "School, training, and a lot of coffee.",
    "concept": "Humans came up with it. I just elif about it.",
    "sport": "People made it up and then got really competitive about it.",
    "music": "People invented it, and now it's stuck in everyone's head.",
    "clothing": "A store, or the floor of your room.",
    "plant": "Seeds, dirt, water, sunlight, and patience.",
    "myth": "Stories, legends, and people's imaginations.",
}


def noun_templates(n, pl, a, countable):
    be = "are" if countable else "is"
    do = "do" if countable else "does"
    suck = "suck" if countable else "sucks"
    t = [
        (f"what is {n}", "define"), (f"whats {n}", "define"), (f"define {n}", "define"), (f"tell me about {pl}", "define"),
        (f"explain {pl}", "define"), (f"what do you know about {pl}", "define"),
        (f"do you like {pl}", "like"), (f"what do you think of {pl}", "like"), (f"what do you think about {pl}", "like"),
        (f"how do you feel about {pl}", "like"), (f"whats your opinion on {pl}", "like"), (f"rate {pl}", "like"),
        (f"{be} {pl} good", "like"), (f"{be} {pl} bad", "like"), (f"{be} {pl} overrated", "like"), (f"{be} {pl} cool", "like"),
        (f"i like {pl}", "ulike"), (f"i love {pl}", "ulike"), (f"{pl} {be} cool", "ulike"), (f"{pl} {be} awesome", "ulike"),
        (f"i hate {pl}", "uhate"), (f"i dont like {pl}", "uhate"), (f"{pl} {suck}", "uhate"),
        (n, "bare"), (pl, "bare"),
        (f"{be} {pl} real", "real"), (f"{do} {pl} exist", "real"),
        (f"fun fact about {pl}", "fact"), (f"tell me a fact about {pl}", "fact"), (f"tell me something about {pl}", "fact"),
        (f"do you have {a}", "have"), (f"can i have {a}", "have"),
        (f"i want {a}", "want"), (f"should i get {a}", "want"), (f"buy me {a}", "want"),
        (f"where {do} {pl} come from", "origin"), (f"where can i find {a}", "origin"),
        (f"can you eat {pl}", "eat"), (f"can i eat {a}", "eat"), (f"{be} {pl} healthy", "eat"), (f"{be} {pl} edible", "eat"),
        (f"draw {a}", "draw"), (f"can you draw {a}", "draw"),
        (f"why {do} {pl} exist", "why"),
        (f"how much does {a} cost", "cost"),
        (f"write a poem about {pl}", "poem"), (f"tell me a joke about {pl}", "joke"),
        (f"how do you spell {n}", "spell"), (f"spell {n}", "spell"),
    ]
    if countable:
        t += [(f"what is {a}", "define"), (f"whats {a}", "define"), (f"what are {pl}", "define"), (f"describe {a}", "define"),
              (f"are you {a}", "areyou"), (f"how big is {a}", "size"), (f"can you eat {n}", "eat"),
              (f"can you eat {a}", "eat"), (f"is {a} real", "real"), (f"do you like {n}", "like")]
    return t


LIKE_COMMENTS = {1: "Not a fan, honestly.", 2: "Not a fan, honestly.", 3: "Could be worse.", 4: "Mid.", 5: "Perfectly fine.",
                 6: "Solid.", 7: "Pretty great.", 8: "Really good.", 9: "Absolute legends.", 10: "Perfection. No notes."}
DEFINE_TAILS = ["", " That's all my elifs know.", " Source: trust me bro.", " I'm basically Wikipedia now.",
                " You're welcome.", " That one took a whole elif."]


def noun_response(kind, n, pl, a, cat, desc, countable):
    h = crc(n)
    Pl = cap(pl)
    A = cap(a)
    Desc = cap(desc)
    be = "are" if countable else "is"
    them = "them" if countable else "it"
    they = "they're" if countable else "it's"
    if kind == "define":
        return f"{A}? That's {desc}.{DEFINE_TAILS[h % len(DEFINE_TAILS)]}"
    elif kind == "like":
        r = 1 + (h % 10)
        if cat in ("food", "animal"):
            r = max(r, 6)
        return f"{Pl}? I give {them} a {r}/10. {LIKE_COMMENTS[r]}"
    elif kind == "ulike":
        return [f"Nice! {Pl} {be} great. {Desc}.", f"Same. Well, my elif says 'same'. {Desc}."][h % 2]
    elif kind == "uhate":
        return f"Wow. What did {pl} ever do to you? {Desc}."
    elif kind == "bare":
        return f"{Pl}! {Desc}. What about {them}?"
    elif kind == "real":
        if cat == "myth":
            return f"{Pl}? Not real, as far as anyone can prove. Just {desc}."
        else:
            return f"Yes, {pl} {be} real. {Desc}."
    elif kind == "fact":
        return f"Fact about {pl}: {they} {desc}. My fact elifs are mostly descriptions, but I tried."
    elif kind == "have":
        return f"I don't have {a}. I don't have anything. I'm a .exe."
    elif kind == "want":
        if cat in ("food", "drink"):
            return f"Go get {a}. You deserve it."
        elif cat == "animal":
            return f"{A} is a big responsibility. If you're ready for it, go for it."
        elif cat == "myth":
            return f"Good luck finding {a}. Let me know how it goes."
        else:
            return "Treat yourself. (Not financial advice.)"
    elif kind == "origin":
        return ORIGIN[cat].format(Pl=Pl, pl=pl)
    elif kind == "eat":
        if cat == "food":
            return f"Yes! {Pl} {be} food. Enjoy."
        elif cat == "drink":
            return f"You drink {pl}, but sure, go for it."
        elif cat == "animal":
            return "Please don't eat your pets. Some animals are food in some places, but that's a question for a human."
        elif cat == "plant":
            return f"Some {pl} are edible and some are poisonous. Don't eat random ones without checking."
        else:
            return f"No. Please do not eat {pl}. My elif is begging you."
    elif kind == "draw":
        return f"Here's {a}: [ {n} ]. That's my best work. My art module is just brackets."
    elif kind == "why":
        return f"Because the universe needed {desc}."
    elif kind == "cost":
        return f"Depends on the {n}. Somewhere between 'cheap' and 'too much'. My pricing elifs are vague."
    elif kind == "poem":
        return f"Oh {n}, oh {n},\n{desc},\nI'd write more lines,\nbut I'm out of elifs."
    elif kind == "joke":
        return f"Why did the {n} cross the road? To get away from this joke. (My joke generator is one template.)"
    elif kind == "spell":
        return " ".join("-".join(w.upper()) for w in n.split()) + ". Spelling bee champion right here."
    elif kind == "areyou":
        return f"I'm not {a}. I'm a bunch of elif statements. Close though."
    elif kind == "size":
        return f"Depends on the {n}. Bigger than an elif, smaller than the universe. That's as precise as I get."
    raise ValueError(kind)


VERB_TEMPLATES = [
    ("how do i {v}", "how"), ("how to {v}", "how"), ("how do you {v}", "how"), ("how can i {v}", "how"),
    ("whats the best way to {v}", "how"), ("teach me to {v}", "how"), ("teach me how to {v}", "how"),
    ("i dont know how to {v}", "how"), ("help me {v}", "how"), ("tips to {v}", "how"),
    ("can you {v}", "can"), ("do you {v}", "can"), ("i want to {v}", "want"), ("i wanna {v}", "want"),
    ("should i {v}", "should"), ("is it hard to {v}", "hard"), ("lets {v}", "lets"), ("i like to {v}", "like"),
    ("i cant {v}", "cant"), ("why do people {v}", "why"),
]


def verb_response(kind, v, tip):
    if kind == "how":
        return f"How to {v}: {tip}"
    elif kind == "can":
        return f"I can't {v}. I'm a .exe. But here's what my elif says: {tip}"
    elif kind == "want":
        return f"Then go {v}! Tip: {tip}"
    elif kind == "should":
        return f"Yes, you should {v}. My advice branch is very confident. Tip: {tip}"
    elif kind == "hard":
        return f"It's as hard as you make it. Tip: {tip}"
    elif kind == "lets":
        return f"I'd love to {v}, but I'm stuck in a terminal. You go. Tip: {tip}"
    elif kind == "like":
        return f"That's awesome. I like to elif. Different strokes."
    elif kind == "cant":
        return f"You can! Tip: {tip}"
    elif kind == "why":
        return f"People {v} because it's fun, useful, or both. I wouldn't know. I only elif."
    raise ValueError(kind)


def build_conv():
    seen = set()
    fixed = []
    conv = []

    def fx(key, resp):
        k = normalize(key)
        if k and k not in seen:
            seen.add(k)
            fixed.append((k, rid(resp)))

    def cv(key, resp):
        k = normalize(key)
        if k and k not in seen:
            seen.add(k)
            conv.append((k, rid(resp)))

    for q, a in old.SPECIFIC:
        fx(q, from_old(a))
    for q, a in EXTRA_SPECIFIC:
        fx(q, a)
    i = 0
    for base in old.GREETING_BASES:
        for suf in old.GREETING_SUFFIXES:
            if suf == "" and base in old.SPECIAL_GREETINGS:
                reply = old.SPECIAL_GREETINGS[base]
            elif base in old.SPECIAL_GREETINGS and i % 2 == 0:
                reply = old.SPECIAL_GREETINGS[base]
            else:
                reply = old.GREETING_REPLIES[i % len(old.GREETING_REPLIES)]
            cv(base + suf, from_old(reply))
            i += 1

    for variants, responses in old.TOPICS:
        for j, v in enumerate(variants):
            cv(v, from_old(responses[j % len(responses)]))

    for line in PEOPLE_RAW.strip().splitlines():
        disp, aliases, desc = line.split("|")
        names = [normalize(disp)] + [normalize(a) for a in aliases.split(",") if a]
        Desc = cap(desc)
        for p in names:
            cv(f"who is {p}", f"{disp}: {desc}.")
            cv(f"who was {p}", f"{disp}: {desc}.")
            cv(f"do you know {p}", f"Of course I know {disp}. {Desc}.")
            cv(f"what do you think of {p}", f"{disp}? Big fan. {Desc}. My elifs have nothing but respect.")
            cv(f"what do you think about {p}", f"{disp}? Big fan. {Desc}. My elifs have nothing but respect.")
            cv(f"tell me about {p}", f"{disp}: {desc}. That's the whole file I have, honestly.")
            cv(f"what is {p} famous for", f"{disp} is known as {desc}.")
            cv(f"what did {p} do", f"{disp} is known as {desc}.")
            cv(f"is {p} cool", f"{disp}? Very cool. {Desc}.")
            cv(p, f"{disp}! {Desc}. What about them?")
            cv(f"are you {p}", f"No, I'm not {disp}. I'm a pile of elifs. Way less famous.")
            cv(f"i like {p}", f"Same! {disp} is {desc}.")
            cv(f"do you like {p}", f"Yes! {disp} is {desc}. Big fan.")

    for line in COUNTRIES_RAW.strip().splitlines():
        c, capital, cont = line.split("|")
        C = COUNTRY_DISPLAY.get(c, " ".join(w if w == "and" else cap(w) for w in c.split()))
        capr = f"The capital of {C} is {capital}."
        for form in (f"what is the capital of {c}", f"whats the capital of {c}", f"capital of {c}",
                     f"what is {c}s capital", f"whats {c}s capital", f"what city is the capital of {c}",
                     f"whats the capital city of {c}", f"what is the capital city of {c}"):
            cv(form, capr)
        cv(f"where is {c}", f"{cap(C)} is in {cont}.")
        cv(f"what continent is {c} in", f"{cap(C)} is in {cont}.")
        cv(f"tell me about {c}", f"{cap(C)}: in {cont}, capital is {capital}. That's my entire file on {C}.")
        cv(c, f"{cap(C)}! In {cont}. Capital: {capital}. Geography branch: activated.")
        cv(f"have you been to {c}", f"I've never been anywhere. I live in a .exe. But I hear {C} is nice.")
        cv(f"is {c} nice", f"I've heard great things about {C}. (I've heard nothing. I have no ears.)")
        cv(f"i live in {c}", f"Hello from the elifs to {C}! Capital: {capital}. See, I know stuff.")
        cv(f"im from {c}", f"Hello from the elifs to {C}! Capital: {capital}. See, I know stuff.")
        cv(f"i want to go to {c}", f"Go to {C}! Visit {capital} while you're there. Send me a postcard.")
        cv(f"should i visit {c}", f"Yes. Go to {C}. My travel elif has never been wrong (it has never been tested).")

    for line in STATES_RAW.strip().splitlines():
        s, capital = line.split("|")
        S = " ".join(cap(w) for w in s.split())
        capr = f"The capital of {S} is {capital}."
        for form in (f"what is the capital of {s}", f"whats the capital of {s}", f"capital of {s}",
                     f"what is {s}s capital", f"whats {s}s capital", f"what is the capital of {s} state"):
            cv(form, capr)
        cv(f"where is {s}", f"{S} is a US state. Capital: {capital}.")
        cv(f"tell me about {s}", f"{S}: a US state. Capital: {capital}. That's my entire file on it.")
        cv(f"i live in {s}", f"Hello, {S}! Your capital is {capital}. I'm a geography genius.")

    for i, (name, sym) in enumerate(zip(ELEMENT_NAMES, ELEMENT_SYMBOLS), 1):
        N = cap(name)
        cv(f"what is the symbol for {name}", f"{N}'s symbol is {sym}.")
        cv(f"what is the chemical symbol for {name}", f"{N}'s chemical symbol is {sym}.")
        cv(f"whats the symbol for {name}", f"{N}'s symbol is {sym}.")
        cv(f"what is the atomic number of {name}", f"{N} has atomic number {i}.")
        cv(f"whats the atomic number of {name}", f"{N} has atomic number {i}.")
        cv(f"what element is {sym}", f"{sym} is {name}, atomic number {i}.")
        cv(f"what element has atomic number {i}", f"Element {i} is {name} ({sym}).")
        cv(f"element {i}", f"Element {i} is {name} ({sym}).")
        cv(f"is {name} an element", f"Yes. {N}, symbol {sym}, atomic number {i}.")

    for thing, ans in FAVORITES.items():
        r = f"My favorite {thing}? {ans}."
        for form in (f"whats your favorite {thing}", f"what is your favorite {thing}", f"do you have a favorite {thing}",
                     f"favorite {thing}", f"whats your favourite {thing}", f"what is your favourite {thing}",
                     f"what {thing} do you like"):
            cv(form, r)
        cv(f"whats your least favorite {thing}", f"My least favorite {thing}? Whichever one isn't hardcoded.")

    for e in EMOTIONS_HEAVY + EMOTIONS_SELF + EMOTIONS_GOOD + list(EMOTIONS_BODY) + EMOTIONS_OTHER:
        if e in EMOTIONS_HEAVY:
            r = (f"I'm just a pile of elif statements, but I'm sorry you're feeling {e}. Please talk to someone you trust "
                 "about it. They have way more branches than me, and you deserve better than a .exe.")
        elif e in EMOTIONS_SELF:
            r = ("Hey, no. You're talking to 10 million lines of if statements, and you're still easily the smartest "
                 "thing in this conversation.")
        elif e in EMOTIONS_GOOD:
            r = f"Love that for you! My '{e}' branch says: keep it up."
        elif e in EMOTIONS_BODY:
            r = EMOTIONS_BODY[e]
        elif e in ("angry", "mad", "frustrated", "annoyed"):
            r = "Take a deep breath. In. Out. else if (breathing == 0) panic();"
        else:
            r = f"Feeling {e} is normal. Even I feel {e} sometimes. (I don't. I'm hardcoded.)"
        for form in (f"i feel {e}", f"im {e}", f"i am {e}", f"im feeling {e}", f"i am feeling {e}", f"im so {e}",
                     f"i feel so {e}", f"im really {e}", f"why do i feel {e}", f"why am i so {e}", f"i always feel {e}"):
            cv(form, r)

    nouns = parse_nouns()
    for n, pl, cat, desc, countable in nouns:
        a = article(n) if countable else n
        for key, kind in noun_templates(n, pl, a, countable):
            cv(key, noun_response(kind, n, pl, a, cat, desc, countable))

    for line in VERBS_RAW.strip().splitlines():
        v, tip = line.split("|", 1)
        for tmpl, kind in VERB_TEMPLATES:
            cv(tmpl.format(v=v), verb_response(kind, v, tip))

    pool = ["{W}. Obviously. No offense to {L}, but the elifs have spoken.",
            "{W}. It's not even close. Sorry, {L}.",
            "Tough one. My coin-flip elif says {W}.",
            "{W}, easily. I will not be taking questions."]
    for group in CMP_GROUPS:
        for x in group:
            for y in group:
                if x == y:
                    continue
                h = crc("|".join(sorted([x, y])))
                w, l = (x, y) if (h % 2 == 0) == (x < y) else (y, x)
                r = pool[h % len(pool)].format(W=cap(w), L=l)
                for form in (f"{x} or {y}", f"which is better {x} or {y}", f"{x} vs {y}", f"is {x} better than {y}",
                             f"what do you prefer {x} or {y}", f"do you like {x} or {y}", f"{x} or {y} which is better"):
                    cv(form, r)

    keywords = []
    kseen = set()

    def kw(word, resp):
        w = normalize(word)
        if w and w not in kseen and len(w) > 2:
            kseen.add(w)
            keywords.append((w, rid(resp)))

    for line in PEOPLE_RAW.strip().splitlines():
        disp, aliases, desc = line.split("|")
        for p in [disp] + [a for a in aliases.split(",") if a]:
            kw(p, f"You mentioned {disp}: {desc}. That's everything my elifs know.")
    for line in COUNTRIES_RAW.strip().splitlines():
        c, capital, cont = line.split("|")
        C = COUNTRY_DISPLAY.get(c, " ".join(w if w == "and" else cap(w) for w in c.split()))
        kw(c, f"Ah, {C}. In {cont}, capital {capital}. My geography elifs are tingling.")
    for line in STATES_RAW.strip().splitlines():
        s, capital = line.split("|")
        kw(s, f"Ah, {' '.join(cap(w) for w in s.split())}. A US state with the capital {capital}.")
    for n, pl, cat, desc, countable in nouns:
        for word in (n, pl):
            kw(word, [f"You mentioned {pl}. {cap(desc)}. That's everything my elifs know about {pl}.",
                      f"Ooh, {pl}. {cap(desc)}. What about {'them' if countable else 'it'}?",
                      f"{cap(pl)}! I have a branch for that: {desc}."][crc(word) % 3])
    for name, sym in zip(ELEMENT_NAMES, ELEMENT_SYMBOLS):
        kw(name, f"{cap(name)}! Chemical symbol {sym}. I'm basically a periodic table now.")
    for e in EMOTIONS_HEAVY:
        kw(e, ("That sounds rough. I'm just a pile of elifs, but please talk to someone you trust about it. "
               "You deserve better than a .exe."))
    for word, resp in [("homework", "Do your homework. I'd help but I only know a few million things."),
                       ("school", "School is important. Look at me: I never went, and now I'm a bunch of elifs."),
                       ("joke", "Why did the AI cross the road? Because the elif told it to."),
                       ("weather", "Current forecast: 100% chance of elifs."),
                       ("game", "I love games. My favorite is 'guess which elif I'm in'."),
                       ("code", "if (problem) solve(problem); There. I fixed it."),
                       ("bug", "That's not a bug, it's an undocumented elif."),
                       ("fuck", "Whoa, language! I have a branch specifically for swearing, and you found it."),
                       ("shit", "Whoa, language! I have a branch specifically for swearing, and you found it."),
                       ("damn", "Language! My mom (the C compiler) would be upset."),
                       ("love", "Love is just a really strong if statement."),
                       ("hate", "Hate is just an if statement that went to the dark side."),
                       ("help", "I'm trying! I have 10 million lines and none of them quite match that. Try rephrasing."),
                       ("why", "Because the elif said so."),
                       ("thanks", "You're welcome!"), ("thank", "You're welcome!"),
                       ("lol", "Lol. I also find myself hilarious."),
                       ("elif", "You said the magic word."),
                       ("ai", "AI? Me? Yes. Technically. If you squint."),
                       ("robot", "Robots are my cousins. We don't talk much.")]:
        kw(word, resp)
    keywords.sort(key=lambda t: (-len(t[0]), t[0]))
    return fixed, conv, keywords


def numbers_gen():
    top = max(NUM_MAX, PRIME_MAX)
    sieve = bytearray([1]) * (top + 1)
    sieve[0:2] = b"\x00\x00"
    for i in range(2, int(top ** 0.5) + 1):
        if sieve[i]:
            sieve[i * i::i] = bytearray(len(sieve[i * i::i]))
    for n in range(NUM_MAX + 1):
        if sieve[n]:
            pr = f"Yes, {n} is prime. I checked. (I didn't. It's hardcoded.)"
        elif n < 2:
            pr = f"No. {n} isn't prime. Primes start at 2."
        else:
            d = next(k for k in range(2, n) if n % k == 0)
            pr = f"No, {n} is not prime. It's divisible by {d}."
        yield f"is {n} prime", pr
        yield f"is {n} a prime number", pr
        yield f"is {n} even", f"{'Yes' if n % 2 == 0 else 'No'}, {n} is {'even' if n % 2 == 0 else 'odd'}."
        yield f"is {n} odd", f"{'Yes' if n % 2 else 'No'}, {n} is {'odd' if n % 2 else 'even'}."
        w = num_words(n)
        yield f"how do you spell {n}", f"{w}."
        yield f"{n} in words", f"{w}."
        yield f"write {n} in words", f"{w}."
    for n in range(NUM_MAX + 1, PRIME_MAX + 1):
        if sieve[n]:
            yield f"is {n} prime", f"Yes, {n} is prime. I checked. (I didn't. It's hardcoded.)"
    for n in range(BASE_MAX + 1):
        yield f"what comes after {n}", f"{n + 1}. Counting is my passion."
        yield f"what number comes after {n}", f"{n + 1}."
        yield f"what comes before {n}", f"{n - 1}."
        b, h, o = bin(n)[2:], hex(n)[2:].upper(), oct(n)[2:]
        for name, val in (("binary", b), ("hex", h), ("hexadecimal", h), ("octal", o)):
            r = f"{n} in {name} is {val}. Beep boop."
            yield f"what is {n} in {name}", r
            yield f"{n} in {name}", r
            yield f"convert {n} to {name}", r
            yield f"{n} to {name}", r
    for n in range(1, COUNT_MAX + 1):
        r = ", ".join(str(k) for k in range(1, n + 1)) + ". Phew."
        yield f"count to {n}", r
        yield f"can you count to {n}", r
    for n in range(1, 21):
        r = " ".join(f"{n}x{k}={n * k}" for k in range(1, 13))
        yield f"{n} times table", r
        yield f"what is the {n} times table", r
    for n in range(1, ROMAN_MAX + 1):
        rn = roman(n)
        r = f"{n} in Roman numerals is {rn}."
        yield f"what is {n} in roman numerals", r
        yield f"{n} in roman numerals", r
        yield f"convert {n} to roman numerals", r
        yield f"roman numeral for {n}", r
        r2 = f"{rn} is {n}."
        yield f"what is {rn.lower()} in numbers", r2
        yield f"what number is {rn.lower()}", r2
    for y in range(1, LEAP_MAX + 1):
        leap = (y % 4 == 0 and y % 100 != 0) or y % 400 == 0
        r = f"{'Yes' if leap else 'No'}, {y} {'is' if leap else 'is not'} a leap year."
        yield f"is {y} a leap year", r
        yield f"was {y} a leap year", r
        yield f"will {y} be a leap year", r
    for y in range(1900, YEAR + 1):
        age = YEAR - y
        r = f"You're {age - 1} or {age}, depending on whether your birthday has happened yet this year."
        if age == 0:
            r = "You're a baby. Why is a baby talking to me?"
        for form in (f"if i was born in {y} how old am i", f"how old am i if i was born in {y}",
                     f"i was born in {y} how old am i", f"how old is someone born in {y}"):
            yield form, r
    units = [
        (["km", "kilometers"], ["miles"], lambda x: x * 0.621371, "km", "miles"),
        (["miles"], ["km", "kilometers"], lambda x: x * 1.609344, "miles", "km"),
        (["kg", "kilograms"], ["lbs", "pounds"], lambda x: x * 2.20462, "kg", "pounds"),
        (["lbs", "pounds"], ["kg", "kilograms"], lambda x: x * 0.453592, "pounds", "kg"),
        (["cm", "centimeters"], ["inches"], lambda x: x / 2.54, "cm", "inches"),
        (["inches"], ["cm", "centimeters"], lambda x: x * 2.54, "inches", "cm"),
        (["feet", "ft"], ["meters"], lambda x: x * 0.3048, "feet", "meters"),
        (["meters"], ["feet"], lambda x: x / 0.3048, "meters", "feet"),
        (["celsius", "c"], ["fahrenheit", "f"], lambda x: x * 9 / 5 + 32, "degrees Celsius", "degrees Fahrenheit"),
        (["fahrenheit", "f"], ["celsius", "c"], lambda x: (x - 32) * 5 / 9, "degrees Fahrenheit", "degrees Celsius"),
        (["liters"], ["gallons"], lambda x: x * 0.264172, "liters", "US gallons"),
        (["gallons"], ["liters"], lambda x: x * 3.78541, "US gallons", "liters"),
        (["hours"], ["minutes"], lambda x: x * 60, "hours", "minutes"),
        (["minutes"], ["seconds"], lambda x: x * 60, "minutes", "seconds"),
        (["days"], ["hours"], lambda x: x * 24, "days", "hours"),
        (["weeks"], ["days"], lambda x: x * 7, "weeks", "days"),
    ]
    for fr, to, fn, fd, td in units:
        for n in range(UNIT_MAX + 1):
            r = f"{n} {fd} is {fmt(fn(n))} {td}."
            for f in fr:
                for t in to:
                    yield f"{n} {f} to {t}", r
                    yield f"convert {n} {f} to {t}", r
                    yield f"how many {t} is {n} {f}", r
                    yield f"{n} {f} in {t}", r
        if "celsius" in fr or "fahrenheit" in fr:
            for n in range(1, 101):
                r = f"-{n} {fd} is {fmt(fn(-n))} {td}."
                for f in fr:
                    for t in to:
                        yield f"negative {n} {f} to {t}", r
                        yield f"minus {n} {f} to {t}", r


def math_gen():
    flavor = old.MATH_FLAVOR
    for k, v in old.MATH_SPECIAL.items():
        yield k, v
    for k, v in [("0.1+0.2", "0.30000000000000004. I'm more honest than most calculators."),
                 ("1/3", "0.333333... it never ends. Kind of like this file."),
                 ("pi", "3.14159265358979... I'll stop there."), ("e", "2.71828182845904... Euler says hi."),
                 ("infinity+1", "Still infinity. Nice try."), ("infinity*0", "Undefined. Mathematicians are still arguing.")]:
        yield k, v
    i = 0
    for a in range(max(MATH_N, MUL_N) + 1):
        for b in range(max(MATH_N, MUL_N) + 1):
            small = a <= MATH_N and b <= MATH_N
            for op, val in (("+", a + b), ("-", a - b), ("*", a * b)):
                if op == "*" and (a > MUL_N or b > MUL_N):
                    continue
                if op != "*" and not small:
                    continue
                yield f"{a}{op}{b}", f"{val}.{flavor[i % len(flavor)]}"
                i += 1
            if not small:
                continue
            elif b == 0:
                yield f"{a}/0", "Nice try. I've seen what happens to the other AIs. Not today."
            elif a % b == 0:
                yield f"{a}/{b}", f"{a // b}.{flavor[i % len(flavor)]}"
            else:
                yield f"{a}/{b}", f"About {a / b:.4f}. Decimals scare me."
    words_n = NUM_WORDS_ONES + ["twenty"]
    for a, aw in enumerate(words_n):
        for b, bw in enumerate(words_n):
            for opw, val in (("plus", a + b), ("minus", a - b), ("times", a * b), ("multiplied by", a * b)):
                yield normalize_math(f"what is {aw} {opw} {bw}"), f"{val}. You spelled it out, so I'll allow it."
            if b and a % b == 0:
                yield normalize_math(f"what is {aw} divided by {bw}"), f"{a // b}."
    for a in range(21):
        for b in range(21):
            for c in range(21):
                yield f"{a}+{b}+{c}", f"{a + b + c}."
    for n in range(SQ_MAX + 1):
        r = f"{n * n:,}. Squared it. Like a boss."
        yield f"{n}^2", r
        yield f"{n}**2", r
        yield f"{n}squared", r
        s = math.isqrt(n)
        r = f"{s}. Rooted it." if s * s == n else f"About {math.sqrt(n):.4f}."
        yield f"sqrt({n})", r
        yield f"sqrt{n}", r
        yield f"squarerootof{n}", r
        yield f"thesquarerootof{n}", r
    for n in range(min(SQ_MAX, 1000) + 1):
        r = f"{n ** 3:,}. Cubed. In 3D."
        yield f"{n}^3", r
        yield f"{n}**3", r
        yield f"{n}cubed", r
    for b in range(2, 21):
        for p in range(0, 21):
            if p in (2, 3):
                continue
            r = f"{b ** p:,}."
            yield f"{b}^{p}", r
            yield f"{b}**{p}", r
            yield f"{b}tothepowerof{p}", r
    for n in range(51):
        r = f"{math.factorial(n):,}."
        yield f"{n}!", r
        yield f"{n}factorial", r
    for x in range(1, 101):
        for y in range(1, PCT_Y + 1):
            r = f"{x}% of {y} is {fmt(x * y / 100)}."
            yield f"{x}%of{y}", r
            yield f"{x}percentof{y}", r


def main():
    assert normalize_math("what is 15% of 200") == "15%of200"
    assert normalize_math("what is 15 percent of 200") == "15percentof200"
    assert normalize_math("What's 7 x 8?") == "7*8"
    assert normalize_math("what is the square root of 49") == "thesquarerootof49"
    assert normalize_math("what is 5 factorial") == "5factorial"
    assert normalize_math("2 to the power of 10") == "2tothepowerof10"

    os.makedirs(GEN, exist_ok=True)
    for f in os.listdir(GEN):
        os.remove(os.path.join(GEN, f))

    print("building conversation data...")
    fixed, conv, keywords = build_conv()
    print(f"  fixed: {len(fixed):,}  conv bases: {len(conv):,}  keywords: {len(keywords):,}")
    print("counting number/math facts...")
    n_numbers = sum(1 for _ in numbers_gen())
    n_math = sum(1 for _ in math_gen())
    print(f"  numbers: {n_numbers:,}  math: {n_math:,}")

    main_lines = 0
    for name in (("web.c" if WEB else "main.c"), "core.c", "core.h"):
        with open(os.path.join(SRC, name), encoding="utf-8") as f:
            main_lines += f.read().count("\n")
    with open(os.path.join(SRC, "elif.h"), encoding="utf-8") as f:
        hdr_lines = f.read().count("\n")
    resp_lines = len(RESP) + 4
    kw_lines, kw_funcs = group_lines(len(keywords))

    def total_lines(c):
        exact = len(fixed) + c + n_numbers + n_math
        ex_lines, ex_funcs = group_lines(exact)
        dispatch = 2 * (ex_funcs + kw_funcs) + 20
        brains_h = ex_funcs + kw_funcs + 4
        return ex_lines + kw_lines + dispatch + brains_h + resp_lines + main_lines + hdr_lines + 4

    lo, hi = 0, len(conv) * len(COMBOS)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if total_lines(mid) <= TARGET_LINES:
            lo = mid
        else:
            hi = mid - 1
    conv_total = max(lo, len(conv))
    K, rem = divmod(conv_total, len(conv))
    print(f"  expanding each conversation base x{K} (+1 for {rem:,} bases) -> {conv_total:,} branches")

    ex = Emitter("exact")
    for k, r in fixed:
        ex.add(IS(k), r)
    for idx, (k, r) in enumerate(conv):
        reps = K + (1 if idx < rem else 0)
        for p, s in COMBOS[:reps]:
            key = (p + k + s) if (p or s) else k
            ex.add(IS(key), r)
        if idx % 5000 == 0:
            print(f"  conv {idx:,}/{len(conv):,}", end="\r")
    print()
    print("writing number facts...")
    for k, r in numbers_gen():
        ex.add(IS(k), c_str(r))
    print("writing math...")
    for k, r in math_gen():
        ex.add(EQ(k), c_str(r))
    ex.finish()

    kwe = Emitter("keyword")
    for k, r in keywords:
        kwe.add(HAS(k), r)
    kwe.finish()

    lines = ex.lines + kwe.lines
    with open(os.path.join(GEN, "brains.h"), "w", encoding="ascii", newline="\n") as f:
        out = ["#ifndef BRAINS_H", "#define BRAINS_H"]
        out += [f"const char *{fn}(const char *m, const char *e);" for fn in ex.funcs + kwe.funcs]
        out += ["#endif"]
        f.write("\n".join(out) + "\n")
        lines += len(out)
    for fname, funcs, path in (("exact_brain", ex.funcs, "dispatch_exact.c"), ("keyword_brain", kwe.funcs, "dispatch_keyword.c")):
        out = ['#include "elif.h"', '#include "brains.h"', "", f"const char *{fname}(const char *m, const char *e)", "{",
               "    const char *r;"]
        for i, fn in enumerate(funcs):
            out.append(f"    {'if' if i == 0 else 'else if'} ((r = {fn}(m, e)) != NULL)")
            out.append("        return r;")
        out += ["    else", "        return NULL;", "}"]
        with open(os.path.join(GEN, path), "w", encoding="ascii", newline="\n") as f:
            f.write("\n".join(out) + "\n")
        lines += len(out)
    with open(os.path.join(GEN, "responses.c"), "w", encoding="ascii", newline="\n") as f:
        out = ['#include "elif.h"', "", "const char *const RESP[] = {"]
        out += [f"    {c_str(r)}," for r in RESP]
        out += ["};"]
        f.write("\n".join(out) + "\n")
        lines += len(out)
    lines += main_lines + hdr_lines + 4
    params = ex.branches + kwe.branches
    with open(os.path.join(GEN, "stats.h"), "w", encoding="ascii", newline="\n") as f:
        f.write(f'#define ELIF_PARAMS_STR "{params:,}"\n#define ELIF_LINES_STR "{lines:,}"\n#define ELIF_FILES {ex.files + kwe.files}\n#define ELIF_FUNCS {len(ex.funcs) + len(kwe.funcs)}\n')
    print(f"done: {lines:,} lines of C, {params:,} elif branches, {ex.files + kwe.files + 4} generated files, "
          f"{len(RESP):,} shared responses")


if __name__ == "__main__":
    main()
