# Project Brief

## What It Does
This app should be able to analyze questions from the LSAT test, practice questions, and tutoring examples to break down the questions into manageable chunks, patterns, and scents to look for. This should hep students break down how to think through questions and make them a lot less stressful and see answering the questions more as a learnable skill than a logical guessing game. This app should be able to analyze students notes and responses and form around their weakest areas in ordered to optimize study time and reduce time spent figuring out what to do next. This app would be most useful for students looking to go to law school while or after taking their undergrad and preparing to take the LSAT exam. This solve's the probem of having to pay for expensive tutoring sessions or needing to wait until the next appointment to feel like you are getting real results from your studies.

## The Intelligent Feature
Claude Receives an LSAT question, response, or study notes, and is able to analyze and return a thoughtful guideline on how to think through the problem, if a response is correct or not and why, analyze study notes and create next questions and tips based on a students struggle areas. 

## Interface
This app will use Flask as it needs to be accessible and approachable for students in the Law field, not people only familiar with a command line interface. This needs to be usable on desktop and mobile.

## Data
This app will work with an email and password from the user from their own input, LSAT questions from free online resources and any training Claude has already received, and user's notes and questions they choose to share with the application. User's data will be tied to their account and each account will be encrypted and stored in a json file locally. Users will be able to retrieve or remove all of their data at any time.

## Stretch Goals
[Two things you'd build if you finish early]
Recurring reminders for study with calendar integration.
Study plans based on user's input timeline.
Deeper tutoring features, like being able to give on the spot quizzes, preventing user's from accessing extra resources.

## Success Criteria
[How will you know this is done? What does a working demo look like?]
I will know this is done when all features are able to be used by a blank user without needing developer support. A working demo looks like a chat interface that takes LSAT questions and returns a simpe and readable breakdown of how to think through the question and remeber a pattern for that type of question moving forward.