Intro
Imagine you had a creative AI assistant
with access to the best image and video
models in the world, trains itself on
[music] elite prompting practices,
masters every model, and generates
content for you while you sleep. Well,
we just built a new skill that lets
claude code, anti-gravity, codecs, or
whatever agentic platform you use to
connect and prompt any generative AI
model in the world. So whether you're
after cinematic shots, UGC style videos,
or product videography, you just
describe [music] what you want, how many
assets you need, and your agent handles
everything for you. [music]
Why this skill?
Generative AI models have gotten scary
good recently. Nano Banana Pro and GPT
Image 1.5 are top tier when it comes to
generating realistic images, and Cling,
VO, Sora, and Seance are best-in-class
for video. But using them properly is
where it starts to get painful. Because
first of all, for you to get results
that actually match your vision, you
usually need to understand complex
prompts and prompting techniques. And if
you want a whole volume of content,
you'll have to prompt these models
manually over and over. Now, automation
tools like Weev and N8N are honestly
great and they help quite a lot because
they let you chain models together and
batch content. But they do come with
their own trade-offs as well. The first
one is around complexity. So workflows
like Weev become a complex spaghetti of
nodes pretty quickly if you start using
them for production. And the other
challenge is that new model updates
usually break your setup. So especially
in today's world when new AI models drop
almost monthly each time you need to go
back in N8N or WV and reconfigure your
nodes just to keep up. And finally,
they're also not that flexible. So if
your automation workflow is already
hardwired, say for vertical videos, you
can just tell your workflow to give you
a landscape video instead. Usually you
need to hard-code a configuration say in
N8N to give you that flexibility. Well,
with the advent of agentic platforms, I
think a lot of these challenges can now
actually be solved. Complex prompts and
techniques can live in the agents
memory, which I'll show in a bit. So,
it's already trained on how you want it
to prompt, and you can even train it to
be even better as you use them more. You
can also request multiple content pieces
in one go without doing that manually
and repeating your prompts every time.
And you also get flexibility. So if you
need to use a different model, if you
want to have 10 seconds instead of 8
seconds, or if you want a landscape
video instead of a vertical video, you
just need to ask. And so this is now
possible if you connect your agents to
these generative models through this
skill that I'm about to show you. So
I'll be giving you guys a demo while
also walking you through the key unfair
advantages of this system as we go. And
also just to mention for this lesson,
I'm using clawed code in anti-gravity.
But if you want to use the default
anti-gravity agents or even open AAI's
codecs, which can also be used in
anti-gravity, the process is pretty much
the same. The first advantage is that
Advantage 1 + Demo
you assume the role more of a creative
director instead of being the prompter.
So you're the one just reviewing and
approving while your AI agent is
handling the labor. So just to give one
example, let's say we want to create
multiple ads for this product that we
want to advertise. All we need to do is
to tag this specific photo, which is
this serum reference JPEG, and just ask
Claude code, hey, can you create 10 ads
with this product? use a mixture of GPT
image 1.5 and Nano Banana Pro across
those 10 ads so that I can compare the
performance of those models and before
you actually do everything end to end.
Can you just show me your step-by-step
process so that I can also show people
what you are about to do? And I just
made that prompt so that you can also
understand the step-by-step process that
it will follow. Because what it's about
to do is basically look at this image,
set them up on Air Table so that I have
proper logging of these ads and then it
will actually craft the prompts for me
including how much that will cost and
just go ahead and generate the images
all by batch. So I'll just ask it to
generate the images now. But obviously
if you want this to run end to end, sort
of like a dark factory is the term that
I've been hearing being used where
basically the AI just runs everything
for you end to end including creating
the videos. That is also an option for
you. And just to show you real time what
it's doing. So it now created the 10 Air
Table records for me which if you
haven't used Air Table before it's
basically a spreadsheet tool sort of
like Google Sheets but the difference is
you can preview images in here and it's
also free to use and integrate into
cloud code or anti-gravity. And what it
did for me is generate multiple unique
image prompts that I can either set up
cloud code to pause at this point so
that I can do sort of a quality check on
each of these prompts if that's
something that I want to do or in what
we did here. I just ask it to create the
images directly so that it's more
automated. So now it's generating those
images. And when it's done, you can see
that it generated those images for us
without me even having to do anything.
So these ones look good because you can
then feed this to a video model which
we'll do in a bit for like UGC content.
And then you also have some images and
content around product shots which you
can use for your e-commerce product
pages or even blow up into 4K resolution
posters that you can use for your store.
And all of that has been handled by
Claude Code. And a big reason why these
image prompts are so well defined and
are such good quality even without me
reviewing it is because I train Claude
code on a lot of best practices around
prompting which I'll show how to do in a
bit. And you can see I generated two
images at a time just so that we have a
higher probability that we'll get the
image that we want. And that part is
important because with these models, if
you've ever worked with them, there's
still a lot of components that are
probabilistic. It's obviously much
better now versus how it was months ago.
But if you're working in production,
it's usually often better to generate,
let's say, two to three pieces of images
per run, so that you can save a bit of
time. And the reason why I'm okay to
actually generate multiple volumes of
images is because right now Cloud Code
the way it's generating these Nano
Banana Pro images is that I have it
connected to my Google AI Studio account
which in case you don't know for quite a
long time now Google gives you $300 in
welcome credits for every Gmail account
that you have. So you're able to use
Nano Banana Pro in there and just
connect cla to it directly which I'll
also show later how to do and it also
gives you access by the way to VO3.1
which is one of the video models. So
practically it allows you to do it for
free. But now let's say we want to not
just have these images as our ads but we
also want them to be videos. Well with
claude code or your aentic platform of
choice you can simply just tell it that.
So to give an example so these images
look great. I think I want to turn into
videos uh let's say row 26 with that
shot of the product on the marble board.
And I just want you to animate these
images so that they are more engaging.
Include row 25 as well. And then our
UGC's. I think the one that turned out
really well is row 19. So pick out let's
see I think is image one better or image
two. I think image one is better. So can
you pick out row 19 um and pick out
generated image one and turn that into a
UGC. So just a script based on what you
know about the brand. So you can
literally see I'm just giving directions
to Claude code there and just rambling
about thoughts on what I think should
happen. And you can see here because I
didn't really give it instructions on
what model to use, it's asking me that
right now. So because I wired it up to
V3.1 and I also wired it up to cling 3.0
0. It has those options. So, let's just
use 3.1 for this one. Or actually, let's
do this. So, for the UGC ad, let's use
Sor2 Pro instead. And for the other two,
which are more studio shots, let's use
V3.1 for one of them and then cling 3.0
for the other. And then I'll just type
that out as a specific direction. And
for the variations per record, we can
either do one or two. Let's go ahead and
do two. And that part, by the way, if
you want your agent to just handle that
automatically, you can also just brief
Claude code to use a default model
whenever you want. You can also see that
I trained this claude code engine to
always show me how much the cost of the
generations will be, which I think is
important throughout this process. But
again, if you just want your agent to
proceed with generating everything on
autopilot, that's an option for you as
well. You just need to tell your agent
on how to do that. So now here you can
see that it created the video prompts
for us. And what is now saying is all
three generation jobs are running in
parallel. So, we'll just wait for that
until it comes. All right. So, now that
our agent has finished with this, you
can see that not only was it able to
specifically pick out the images that we
want to be animated, which it has done
correctly, it was also able to craft
these prompts that is already pretty
high quality. So, you can see it
provided the dialogue, provided the
action, plus some camera specs around
what we want, and also was able to use
the model that we dictated for it. So,
if we were to preview the video that it
did for us. Okay, so I have been using
this Esme serum for like 2 weeks now and
honestly my skin has never felt this
smooth.
So that one is Sor 2 Pro and then for
the more sort of cinematic studio
product shots we use Cling 3.0 to
animate this shot and VO3.1 to animate
this one. [music]
And all of that work using different
models, crafting the prompts and even
calling on the models. All of that was
handled by our AI agent, which is CL
code in this case. And all we did was
give it direction. So you're literally
the creative director. You are not the
prompter in this whole equation. Now the
Advantage 2 + adding any AI model
second advantage is that this agent
system is self-learning and never
obsolete. It can learn from your work
and it can also train itself on best
practices. So as you work with them more
and you work with these agents on your
setup, you can actually slowly teach
them about the best practices to do it.
And just to show you that we can just
ask cloud code, hey, can you share some
of the best practices, principles that
we worked on together to get you to a
point where you can actually craft
prompts in my style and using our
techniques? And what it will probably do
is look at this documentation that we
have around prompt best practices. And
this is a pretty long document. You can
see it's something like let's see 387
lines long that I didn't write myself. I
just had Claude code do this. But you
can see a bit of the principles around
this whole document is that when it's
creating UGC's, it's good to use these
words in the prompt so that you get a
more realistic looking character. It has
principles around being more specific,
principles around skin details and some
words to help with that so that it knows
what to do. And then it has different
prompt frameworks as well that I trained
it on. So for influencers, it's using
this Bopa consistency framework. This
seal cam framework are good for
cinematic or hero content and so on and
so forth. And there's multiple ways by
which you can train cla code in your way
of working. Let's say you already have
like a database of prompts for your
specific niche. Then you can just feed
that to claude code. In our case, for
example, in the community, let's say we
have these N8N workflows that we created
in the past. What I can just do is copy
all of these notes and copy them to my
clipboard. I can just send them to
Claude code and say, "Hey, can you take
a look at this N8N workflow and gather
any learnings from it on how you can
prompt better? give me a download of the
principles that you are able to take
away so that I can pick and choose which
ones I want added to your training data
set. And so this is useful because each
of us probably has different use cases
for AI. Some are into branded content,
some are probably creating it for
faceless media and then maybe some are
onto film making. But as you develop
more the specific problems that are
needed for your niche, then you can just
feed them to claude code and have it
sort of absorb the best practices so
that the longer that you use it, the
better it becomes. So you can see here
it actually provided me a few
principles. Some of these I already
trained it on. So let's say hey so some
of these are already in your best
practices but I think number two on text
and product fidelity I want you to just
add that to your best practice
references. That principle around
capping dialogue length and enforcing a
more conversational tone. So whenever
you need a dialogue for a prompt or
whenever we need a script for the video
itself that is good. And number five
around using a structured format like
YAML is actually interesting. So let's
add those in. And so what it's now going
to do is simply look at all of that text
and add it to its prompt best practices
markdown file, which is basically just a
long text file that it can use as
reference. And the other advantage
within this bucket is that it won't go
obsolete because it's easy to update
whenever new models drop. So past few
days, Cance 2.0 Zero has been gathering
a bit of steam and from what we know
internally I think the API for this is
going to drop next Monday but the way to
integrate these models so that cloud
code has access to it is pretty much the
same across the board and all you need
to do is to go to the AI model
aggregator of your choice keyai is one
of them file.ai is also quite popular as
well as waves.ai and since cense 2.0 is
not yet released let's say you want to
just integrate cling 3.0 zero for now.
You just go to that models page and then
under the API section here, it used to
be that you need to read through these
yourself so that you understand how it
works. But now with tools like cloud
code and anti-gravity, you can just copy
this page, which you can see here, it
will copy to your clipboard a markdown
or text file for large language models.
And if we just ask our agent, hey, can
you integrate this API into our
workspace? And then we just provide that
documentation that we just copied, it's
now going to do all of the heavy lifting
in order to do that for us. And there
you go. it was able to absorb all of the
different modes and parameters. So
whether you want to use standard or pro
or whether you want to choose the
duration of the video. Now you can just
dictate that to cloud code and it will
generate those videos for you depending
on the specs that you want or you can
just have cloud code decide those for
Advantage 3 + Multi-agent demo
you. Now the third advantage is that you
can actually spawn multiple agents and
multiple models simultaneously. And so
if you're working on big projects, if
you've generated with these AI models,
you know that a big component is the
waiting time in order for you to review
your output. So for example, let's say
we're creating directing for this
lipstick brand and I want to create a
couple of image ads and studio shots
using this product, but I also want to
feed Claude code this image so that it
has context on the different variations
and product angles that I want. That is
something that you can do as well. So
for example, hey, can you create three
image ads for this lipstick brand? It's
a premium brand, so make sure to use
dark backgrounds for it. But I do want
you to learn from the layout of this
product shot 9x9 grid to pick out the
ones that would most apply to this
brand. And then if we just tag the right
references so that we can give Cloud
Code more guidance there. What it's now
going to do is create those images for
us in the background. And while that's
happening, let's say we need to create
video ads for this same product, but
this time we want the video ads to
feature a model just like this. Well,
what you can simply do is spin up a new
agent through this plus icon and say,
"Hey, can you create video ads for me?
Let's use VO3.1 as well as Nano Banana
Pro 4Ds where essentially I like this
style of the close-up ad but just have
models a diverse set of models have the
lipstick being used. So we can just
provide that reference for our model so
that it knows what it needs to do and
say we need to create new images for
another product entirely. So let's say
this matcha product but we want this
specific effect where you have like
different products floating within
space. So what we can just do, hey, can
you create a few image ads for me
featuring this matcha brand, but I do
want this sort of floating objects
effect where the different matcha
ingredients are floating around the AI
character that we have in the middle.
Make sure to emphasize real ingredients
as well as the fact that this is geared
towards the Japanese target market. And
then we fire that off. And now three
agents are now working for you to use
those different models and create the
content for you even if you step away
from your computer. And now once those
multiple agents have done their job, you
can see we have multiple images here of
that lipstick image using Nano Banana
Pro and also replicating that style that
we wanted of a more close-up shot. This
one turned out quite well. You can see
her pores in here. So the realism is
really next level, especially when you
use Nano Banana Pro. And so if you want
to animate this into a talking head
video, that's something that you can do
as well. This one is a bit more
stylized, but you can see how preserved
the product is, how good the skin
textures are. And this one, I even
animated it to cling 3.0 true. same
agent. And this is the result that it
came up with. [music]
[music]
And if you remember, we also requested
for some studio shots. So these are the
results that we got. And just to try it
out, I also had that agent create and
animate the videos for us.
And you can see this is really high
quality, right? Cling 3.0 basically
handled all of the rendering of this for
us. And not only was it able to preserve
the look of it, it even preserved, if
you look at our original product, that
very subtle cut of the Guerilla brand in
this lipstick. And it was able to do
that without me having to write any
prompts. And finally, for our matcha
example, essentially we had this product
be placed in the center. and our agent
decided the whole setting plus the actor
and also the ingredients to put here. It
even created a second variation that
features a male model. But since we
asked for Japanese characters, it was
also able to follow that instruction.
And similarly, when I asked for a video
prompt, it was able to write that down
along with using the framework that we
taught it and it came up with videos
like these. [music]
Advantage 4
And the fourth advantage is that it's
actually much easier to use and set up
because you don't need any complex
wiring, no node spaghettes in order to
set this up. You can just describe what
you want and claude code will do your
tasks for you. So if you compare it to
another popular platform for creating
content like we workflows are honestly
quite complex to use. And the reason why
you can see there's like a spaghetti of
nodes in here is because in tools like
Weevi if you need to generate let's say
multiple images. You need to have a
specific node for each and every one of
them just like this. But if you're
working with an AI agent you can just
tell it to create like 10 images for you
and it will do that automatically.
Another example is that previously to
set up something like this in N8N a
common pattern for running these models
is that you have to set up some sort of
polling mechanism wherein you pass in
the request. Let's say this one is
creating a video with claim 3.0. You set
up a wait node in order to wait for that
generation to finish and then you check
if that video is already available
because if not then this switch node
will just pull and route this node back
to processing in order to wait a bit
more. Now this is probably good for like
simple workflows but what's great about
working with AI agents like cloud code
is that you can see that it is doing the
waiting for me. So it knows that
claiming 3.0 typically takes 2 to 4
minutes and it does all of that polling
under the hood without me having to set
anything up. And to add to that, if in
case you have multiple providers set up
on your workspace like I do, you can see
that it detected that wave speed
actually resulted to a timeout after 10
minutes of generating a video. And so
what it's doing is use key AI instead
automatically to see if it can generate
the videos that way. The fifth benefit
Advantage 5
is that when you're using an AI agent
system, you actually get more
flexibility on models. Plus, it is also
less expensive overall. Let's take for
example Higfield.AI. Now, Hicksfield is
basically just a rapper on these models,
but they require you to pay a monthly
subscription and have actually been
criticized quite a lot recently because
of their sort of heavy-handed tactics
when it comes to marketing their
platform. So, I won't go into too much
detail, but if you just Google Higsfield
issues, then you'll find several news
articles including Forbes talking about
this as well. But basically, all these
platforms do is just allow you to
connect to these same models. And you
also have to type in the prompts
yourself, which by the way, if you know
where to look and with a lot of the
platforms that we're using in this
channel, since we don't take
sponsorships from these platforms who
approach us, so we can remain unbiased,
you can see that KAI, for example, they
offer all of these same models at much
cheaper prices. And another example I
gave in the beginning is that you can
actually take advantage of the Google
Cloud $300 welcome credit to use Nano
Banana Pro and VO. But the problem with
Key is mainly on reliability issues.
They're sometimes quite slow. And so the
two other providers that we usually use
is FA AI as well as Wavespeed AI. I
think Wavespeed has slightly cheaper
prices versus FAL. Depends on which
model that you're using. But what's
great about these two platforms is that
they give you so much more access to the
models that are available beyond just
the ones that are given by the big names
like Google, OpenAI, and Clling. So if
you go to file AI's explore page, you
can see they have probably more than 400
models at this point where they have
like 3D models, they have different
imagetovideo models. And then similarly
for waves AI, they also have that same
database of models that you can access.
And all of these, by the way, if you
just give the same documentation to
cloud code, you can integrate it
directly without you even having to set
up anything. Now I think it is good to
mention though that if you're using
cloud code, it is only available in
cloud pro subscriptions. But the good
thing about this subscription is it
doesn't just give you access to cloud
code. It also gives you access to
co-work. It also lets you try Entropic's
latest models like Opus. Or if you don't
want to use Cloud Code and instead just
use anti-gravity's default agent, you
can actually try that for free. And if
you have a Gemini subscription to them,
then apart from the other tools that
Google gives you in that plan, it also
gives you access to anti-gravity at more
rate limits. And then thirdly, since a
lot of people use chat GPT, you can just
use codeex. So that's something that you
can also use from within anti-gravity.
And similar to the model of entropic and
Google, codeex is also included in their
chat GPT plus subscription. So if you're
already subscribed to CHAGPT then just
use codeex because that is the agentic
platform that comes with your
subscription already. But the point
being if you're in the AI space most
likely you may have a subscription
already with chatbt in which case you
can just use codeex gemini pro in which
case you can just use the anti-gravity
default agents or if you have a
subscription to claude then you use
cloud code. So in that way you can
centralize all of your subscriptions
into just one tool which is probably why
a lot of people are saying that SAS
platforms are losing their edge because
a lot of the work that we're doing
including these creative tasks are
slowly but surely being offloaded to
agents like these. So there I think this
Set up
is a great alternative to how things are
being run now in the content AI
generation space. So if you haven't
tried claude code or anti-gravity yet,
this might be a good signal for you to
test it out. And if you are setting it
up for your own workspace, what you can
do is to set up a framework similar to
what I did using this specific
structure. And this is a very simple
create framework, which stands for
essentially the folders that you need to
organize in order for your claude code
or anti-gravity to be able to work with
your files better. And if I jump to my
system here, you can see I have the same
thing set up where Claude, which stores
all of the knowledge and commands and
directives of your AI agent. So it has
your API keys in this environ. And that
would also include this cloud.md which
is basically a text file that is several
lines long and this contains all of the
instructions that we gave cloud code so
that it can effectively function as our
creative AI agent. Now if you're using
anti-gravity this will be a dot agent.
It functions very similarly but just
think of this as the brain of your AI
agent. The next one is going to be your
references and these are all of the
inputs that you are providing as
references for your creative AI agent.
So let's say for example you have images
of your brand. You may have references
around the style that you want to create
or recreate. You can even have multiple
product shots that you get from online.
So the cloud code can analyze these
images and craft prompts that will
recreate these images for you. And of
course this also contains your best
practices for prompts which you can just
continuously feed to cloud code so that
it updates or self-updates this
documentation for you. And then the last
is the tools. And think of this as sort
of the workflows that your agent has
access to. So if you've worked with nadn
orate.com before then each of these py
files which if you open them they are
all just python code and you don't need
to understand each of these what they
basically do is take in some inputs
let's say some reference image or a
specific command and depending on the
complexity of your setup. What cloud
code does is just use this python tool
to route let's say that this specific ad
or creative you wanted to route to sora
2. This specific creative you wanted to
route to cling. These Python workflows
are basically code that helps your AI
agent route those tasks more
effectively. And they're also the ones
that update your Air Table. They're also
the ones that generate your video, do
your video analysis, and basically
anything that you need. And to make this
Shortcut for setup (skill)
easy, I shared this whole prompt right
in the description below so that you can
just give this to your AI agent, whether
it's codeex, flood code, or
anti-gravity, and it will guide you
through the setup. And also, if you're
part of the RoboNuggets community, you
can just download my whole setup here so
that you can replicate what I have. And
when you import that to your agent, that
instantly gives you all of these tools
that I have here, including the
connection to all the different image
and video models that I featured on this
channel, plus these prompt best
practices that we will continuously
update as well. And lastly, just to
emphasize, because these are all just
Python files and markdown files, you can
use it if you're using cloud code, if
you are using the native default
anti-gravity agents, or if you're using
OpenAI codeex, whichever subscription
that you have, you can work with it
pretty much the same way. And if you
want to go deeper and learn how to
actually earn from the AI skills that
you're developing, then check out the
Robonets community. There's several
courses here around learning and earning
from AI with training certification, a
community of over a thousand AI
practitioners to build your network and
paid opportunities and collaborations
being shared regularly. And also, we
recently partnered with 500 plus of the
best AI tools to give you deals and
discounts if you're on the annual plan,
which hopefully makes your investment
worthwhile. Just see if that's for you,
but if not, that's completely all right
as well. That's it for this one. I'll
see you guys next time. Thank you.