## Title: memento: a persistent agent for deep hypothesis evaluation based on knowledge graph long-term memory.

## Research Goals:

 

## Abstract

## Introduction

The guiding hypothesis of this work is that high-quality, scalable hypothesis evaluation would be highly valuable for the practice of science.

(provide a brief discussion of the reasons behind that hypothesis. One of them is that AI systems are able to generate large numbers of plausible hypotheses, far beyond the ability of humans to practically review. )

Taking that as a goal, we propose to create an automated method to (1) perform deep research to find experimental data relevant to a hypothesis and (2) either analyze that data or evaluate analyses already performed on that data, and (3) aggregate those findings to produce a net evaluation of the hypothesis.

This contrasts with methods that seek to find statements in the scientific literature that either directly assert that the entire hypothesis is true or which assert that component sub-hypotheses are true.

The strategy of basing evaluation on experimental data is rooted in Karl Popper's principle of falsification. Evaluation takes the form of tests that attempt to falsify the hypotheisis, where confidence is based on the range, relevance, and quality of the the tests that it passes. Or does not pass.

The meaning of relavance and quality includes an evaluation of the translation of hypotheses that are not practical to test into hypotheses which are practically testable. This translation must ultimately identify specific experiments where the outcome can be taken as meaningful evidence for falsification. For example, if I hypothesize that a protein is a transcription factor that regulates gene X, then I might reasonably propose ATAC experiments as having the ability to provide evidence to falsify that claim on the basis that binding to regulatory sites for the gene by that protein is required for regulation.

Recent work in the field has taken this approach and demonstrated hypothesis evaluation using a small number of datasets.

In this work, we seek to extend the depth and rigor of the evaluation process with a sysstem that (1) evaluates the logical consistency of a hypothesis (1) searches the literature and known public databases to find relevant experimental data, (2) takes action to obtain the data, (3) evaluates the methods used in the production of the data, and (4) evaluates the results as to what degree they falsify/fail to falsify the hypothesis.

A key point of such a system is that it should challenge assumptions of the experiments. For the system to be practical, it must budget what it chooses to challenge, making decisions about what assumptions of the original hypothesis or derived practical experiments are (1) least credible and (2) most critical.

It should be emphasized that data that inspire the hypotheses do not have any special status except that the methods and experimental conditions of those experiments might be known in greater detail than existing data found in the literature and public databases. 

We do not, in this study, investigate the issue of automating discovery science. Discovery-drive science entails experiments designed to produce data that could inspire hypotheses and the proposal of experiment plans to test those hypotheses. That process can also include prioritization of hypotheses based on practical matters and the value of hypotheses if validated and we do not address those issues.

The realization of such a system poses significant challenges. Notably, it must be persistent and resourceful, able to evaluate its progress over the course of a long investigation process, to plan and re-plan its actions. It must remember what it has done, not repeating actions. It must make qualitative decisions on when to persist in a line of investigation and when to move on, based on what data sources it discovers. 

We here present Memento, an AI Agent framework that maintains a long-term memory using a knowledge graph to store an explicit representation of plans, an episodic history of its actions and results, and factual knowledge.


## Results



## Discussion

## Acknowledgements

## References
