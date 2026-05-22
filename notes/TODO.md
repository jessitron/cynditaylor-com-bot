# TODO

- there is something about: after 15m (?) the VM isn't cached anymore on AgentCore, and it can lose context. I want to explore what happens then. If I reply to an email promptly, is the whole prior convo in context? If I reply an hour later, is it? ... or maybe it was 8 hours, I forget. Also try an email the next day.

- test failure to send ema il reply. Do I find out? (Yes, I do, I saw it in prod https://ui.honeycomb.io/modernity/environments/cynditaylor-com-bot/datasets/cynditaylor-com-bot/result/uHixxzKiYDz/trace/cUojRTCHo3p?fields[]=s_name&fields[]=s_serviceName&span=2ab24f8280773b3c)
- after send_reply, the agent takes another turn, outputting a message that goes nowhere. Silly.
- make replies look nicer, like be 'from' whoever I sent it to, and continue the subject line
- the agent doesn't need called until after the workspace is synced and the email retrieved.
- have the commit add the thread ID and email content
- its only write command is the whole file. That seems bad
- give it a tool to email me directly. Can it forward Mom's email and make it part of the same thread? How would that work? Even just FYI, it's welcome to send me commentary.
- have it (the tool) add the email body to the telemetry. Also on email send.
- teach it to resize the images appropriately. It prolly needs to get image properties, and also tools to manipulate them.
