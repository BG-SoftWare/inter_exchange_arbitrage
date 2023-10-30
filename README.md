[ENG](#ENG) || [RUS](#RUS)

# ENG

<h1 align=center>Inter-Exchange Arbitrage</h1>

This project is a program to automate the search and implementation of inter-exchange arbitrage. That is, assets are traded on different platforms (exchanges).
In this case, a trader earns on the difference between the rates of one asset on different exchanges.
Since the arbitrage window in such cases is very short (from several milliseconds to several minutes depending on the exchanges), it is very difficult to do it manually.

<h2 align=center>Contents</h2>

1. [Features](#Features)
2. [Technologies](#Technologies)
3. [Preparing to work](#Preparing-to-work)
4. [Usage](#Usage)
5. [DISCLAIMER](#DISCLAIMER)

## Features
The main features of this application include:
  + fully autonomous (the user only needs to make initial settings and run the program);
  + easy to scale (microservice architecture allows adding modules without modifying existing code);
  + use of gRPC (increases the speed of interaction and saves the amount of information transferred between modules);
  + each module (gRPC adapter, business logic) can be located on different servers;
  + any number of currency pairs (each running copy processes one pair (for example, BTCUSDT) on two exchanges. You can run the required number of copies of the program, preliminarily changing the settings for the required currency pairs);
  + easy adaptation to different exchanges.

## Technologies

| Technology | Description |
| ----------- | ----------- |
| Python    | Programming language in which the project is implemented   |
| MySQL    | Relational database for storing transaction history   |
| SQLAlchemy    | SQL toolkit and Object Relational Mapper that gives application developers the full power and flexibility of SQL   |
| grpcio    | With the help of gRPC in this project "communication" between different modules is realized, which allows to increase the speed of interaction and significantly reduce the amount of transmitted information   |
| requests    | An elegant and simple HTTP library for Python   |

## Preparing to work
1. Install [Python](https://www.python.org/downloads/)
2. Download the source code of the project
3. Deploy the virtual environment (venv) in the project folder. To do this, open a terminal in the project folder and enter the command:  
   `python3 -m venv venv`
4. Activate the virtual environment with the command  
   `source venv/bin/activate`
5. Install the project dependencies, which are located in the requirements.txt file. To do this, enter the command in the terminal:  
   `pip install -r requirements.txt`
6. Change the values in the file `definitions.py`
7. Change the values in the file `.env.example` and rename it to `.env`

## Usage
To start, specify the name to be assigned to the process in the buildname file and run the start.sh file (in the current terminal window) or the start_in_background.sh file (if you want to run this as a background process) for execution.

## DISCLAIMER
The user of this software acknowledges that it is provided "as is" without any express or implied warranties. 
The software developer is not liable for any direct or indirect financial losses resulting from the use of this software. 
The user is solely responsible for his/her actions and decisions related to the use of the software.

---

# RUS

<h1 align=center>Inter-Exchange Arbitrage</h1>

Этот проект представляет собой программу для автоматизации поиска и реализации межбиржевого арбитража. То есть активы торгуются на разных площадках (биржах).
В таком случае трейдер зарабатывает на разнице между курсами одного актива на разных биржах.
Поскольку арбитражное окно в таких случаях очень короткое (от нескольких милисекунд до нескольких минут в зависимости от бирж), вручную это делать очень сложно.

<h2 align=center>Содержание</h2>

1. [Особенности](#Особенности)
2. [Технологии](#Технологии)
3. [Подготовка к работе](#Подготовка-к-работе)
4. [Использование](#Использование)
5. [ОТКАЗ ОТ ОТВЕТСТВЕННОСТИ](#ОТКАЗ-ОТ-ОТВЕТСТВЕННОСТИ)

## Особенности
Основные особенности этого приложения включают в себя:
  + полная автономность (пользователю необходимо лишь сделать начальные настройки и запустить программу);
  + легко масштабировать (микросервисная архитектура позволяет добовлять нужные модули не изменяя при этом уже существующий код);
  + использование gRPC (увеличивает скорость взаимодействия и экономит количество информации, передаваемое между модулями);
  + каждый модуль (gRPC-адаптер, бизнес-логика) могут находиться на разных серверах;
  + любое количество валютных пар (каждая запущенная копия обрабатывает одну пару (например, BTCUSDT) на двух биржах. Вы можете запустить нужное количество копий программы, предварительно изменяя настройки под нужные валютные пары);
  + простота адаптации под разные биржи.

## Технологии

| Технология / Библиотека | Описание |
| ----------- | ----------- |
| Python    | Язык программирования, на котором реализован проект   |
| MySQL    | Реляционная база данных для хранения истории сделок   |
| grpcio    | При помощи gRPC в этом проекте реализовано "общение" между различными модулями, что позволяет увеличить скорость взаимодействия и значительно уменьшить количество передаваемой информации   |
| SQLAlchemy    | Комплексный набор инструментов для работы с реляционными базами данных в Python   |
| requests    | HTTP-библиотека для Python. Используется для отправки HTTP-запросов и получения ответов   |

## Подготовка к работе
1. Установите [Python](https://www.python.org/downloads/)
2. Скачайте исходный код проекта
3. Разверните виртуальное окружение (venv) в папке с проектом. Для этого откройте терминал в папке с проектом и введите команду:  
   `python3 -m venv venv`
4. Активируйте виртуальное окружение командой  
   `source venv/bin/activate`
5. Установите зависимости проекта, которые находятся в файле _installation/requirements.txt_. Для этого в терминале введите команду:  
   `pip install -r installation/requirements.txt`
6. Измените значения в файле `definitions.py` на подходящие Вам
7. Внесите изменения в файл `.env.example` и переименуйте его в `.env`

## Использование
Для запуска необходимо указать имя, которое будет присвоено процессу, в файле buildname и запустить на исполнение файл start.sh (в текущем окне терминала) или файл start_in_background.sh (если Вы хотите запустить это как фоновый процесс).

## ОТКАЗ ОТ ОТВЕТСТВЕННОСТИ
Пользователь этого программного обеспечения подтверждает, что оно предоставляется "как есть", без каких-либо явных или неявных гарантий. 
Разработчик программного обеспечения не несет ответственности за любые прямые или косвенные финансовые потери, возникшие в результате использования данного программного обеспечения. 
Пользователь несет полную ответственность за свои действия и решения, связанные с использованием программного обеспечения.

