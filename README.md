# FoodieVent-The-Fully-Developed-Web-Application-Solution-Event-Management-System

## Introduction

A fully developed web application solution for an event management system. Developed in a team by Renny Matis, Boon Leon, Christina Antony Sankoorikal, and Samantha Cray.


Clone it to your local machine through Git CLI with the command below:

```bash
git clone https://github.com/RennyMatis2000/Fully-Developed-Web-Application-Solution-Event-Management-System.git
```

---

## Getting Started

### Prerequisite

Before setting up the environment, navigate to the project folder where `main.py` and `requirements.txt` are located:

```bash
cd a2_starter_code/a2_group11
```

Then, install the dependencies by creating and activating a virtual environment.

> **Windows: Use Command Prompt (cmd.exe)**
>
> Open **Command Prompt** in this folder and run:
> ```cmd
> python -m venv venv
> venv\Scripts\activate
> pip install -r requirements.txt
> ```

> **macOS/Linux**
> ```bash
> python3 -m venv venv
> source venv/bin/activate
> pip install -r requirements.txt
> ```

---

## Setting Up the Database

Before starting the app for the first time, you need to create the database tables:

```bash
python create_db.py
```

## Running the Project

Make sure you are in the application folder and the virtual environment is active before starting the application:

```bash
python main.py
```

---

## Project Structure (will look something like)

```plaintext
Fully-Developed-Web-Application-Solution-Event-Management-System/
│
├── a2_starter_code/
│   └── a2_group11/
│       ├── venv/
│       ├── website/
│       ├── main.py
│       ├── requirements.txt
│       ├── static/
│       ├── templates/
│       └── ...
└── README.md
```
