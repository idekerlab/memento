
Test: explicit instruction to build a plan
Goal: make an inactive multistep plan to perform Action A, where A depends on B and C, B and C depend on D 
Expected outcome:
Actions A,B,C,D 
Relationships A<-B, A<-C, B<-D, C<-D

Test: make a plan where the goal requires one execution action dependent on verification of input actions

Goal. Review hypothesis 1317 using prompt template 1316. 

Expected outcome:
Action B. Perform an LLM query with 1317, 1316
Goal <- B
Action C. verify that 1317 is an existing hypothesis
B <- C
Action D. verify that 1316 is an existing prompt template, checking its input requirements
B <- D

Cases:
Both entities exist and are the expected types
One or more does not exist
1317 isn't a hypothesis
1316 isn't a prompt template
1316 has additional input requirements
1316 isn't about reviewing hypotheses


