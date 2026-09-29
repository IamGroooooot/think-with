---
type: regex
target: last_message
match: contains
flags: i
---
(billing[^\n]{0,60}users|users[^\n]{0,60}billing)[^\n]{0,40}(서로|상호|mutual|each other|both ways|양방향|순환|cycle|circular)|billing[^\n]{0,40}(↔|<->|⇄|⇆|◀[─═]*▶|◄[─═]*►|<-+>)[^\n]{0,40}users|users[^\n]{0,40}(↔|<->|⇄|⇆|◀[─═]*▶|◄[─═]*►|<-+>)[^\n]{0,40}billing|(cycle|순환|circular)[^\n]{0,60}(billing[^\n]{0,40}users|users[^\n]{0,40}billing)
