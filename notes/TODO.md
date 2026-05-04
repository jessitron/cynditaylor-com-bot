# TODO

- test failure to send email reply. Do I find out? (Yes, I do, I saw it in prod https://ui.honeycomb.io/modernity/environments/cynditaylor-com-bot/datasets/cynditaylor-com-bot/result/uHixxzKiYDz/trace/cUojRTCHo3p?fields[]=s_name&fields[]=s_serviceName&span=2ab24f8280773b3c)
- after send_reply, the agent takes another turn, outputting a message that goes nowhere. Silly.
- make replies look nicer, like be 'from' whoever I sent it to, and continue the subject line
- the agent doesn't need called until after the workspace is synced and the email retrieved.
- have the commit add the thread ID and email content