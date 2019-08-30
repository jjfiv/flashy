from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QHBoxLayout,
    QMessageBox,
)
from PyQt5.QtGui import QPixmap
from functools import partial
import os
from bs4 import BeautifulSoup
import attr
from typing import List, Union
import sqlite3
import random


def connect_db(dbpath="learning.db"):
    rv = sqlite3.connect(
        dbpath, timeout=5, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
    )
    rv.row_factory = sqlite3.Row
    return rv


@attr.s
class Student(object):
    name = attr.ib()
    email = attr.ib()
    id_num = attr.ib()
    image_src = attr.ib()
    _image = attr.ib(default=None)

    @staticmethod
    def from_row(trow, rel_path):
        cells = [t for t in trow.children if t.name == "td"]
        # name, email, cell, advisors, id#, class, majors
        info_cells = [
            c.get_text() for c in cells[1].find_all("tbody")[0].find_all("td")
        ]
        name = info_cells[0]
        email = info_cells[1]
        id_num = info_cells[4].split("ID: ")[1]
        image_src = os.path.join(rel_path, cells[0].find_all("img")[0]["src"])
        assert os.path.exists(image_src)
        return Student(name, email, id_num, image_src)

    def first_last(self):
        (last, first) = self.name.split(",")
        return "{} {}".format(first.strip(), last.strip())

    def get_image(self):
        if self._image is None:
            self._image = QPixmap(self.image_src).scaledToHeight(200)
        return self._image


class MainWindow(object):
    def __init__(self, students: List[Student], db, k=5):
        self.db = db
        self.students = students
        self.choices: List[Student] = []
        self.correct: Union[Student, None] = None

        self.app = QApplication([])
        self.window = QWidget()
        self.vlayout = QVBoxLayout()
        self.num_trials = QLabel("Labels done: ...")
        self.image_label = QLabel("Image Goes Here")
        self.vlayout.addWidget(self.image_label)

        self.hbox = QWidget()
        self.vlayout.addWidget(self.hbox)

        self.hlayout = QHBoxLayout()
        self.buttons = [QPushButton("Button {}".format(i)) for i in range(k)]
        for (idx, b) in enumerate(self.buttons):
            self.hlayout.addWidget(b)
            print("Init: {}".format(idx))
            b.clicked.connect(partial(self.on_button_click, idx))

        self.hbox.setLayout(self.hlayout)
        self.window.setLayout(self.vlayout)

        self.setup_problem()

    def setup_problem(self):
        random.shuffle(self.students)
        self.choices = sorted(self.students[: len(self.buttons)], key=lambda x: x.first_last())
        self.correct = random.choice(self.choices)
        for (button, student) in zip(self.buttons, self.choices):
            button.setText(student.first_last())
        self.image_label.setPixmap(self.correct.get_image())

    def num_labels(self):
        return self.db.execute("select count(*) from train_log").fetchone()[0]

    def on_button_click(self, button_index: int):
        assert self.correct is not None
        correct = self.correct.email
        guess = self.choices[button_index].email
        msg = QMessageBox()
        self.db.execute(
            "insert into train_log(actual, guess, created) values (?,?,current_timestamp)",
            (correct, guess),
        )
        if correct == guess:
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Correct! That is {}.".format(self.correct.first_last()))
            msg.setWindowTitle("Correct")
        else:
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Error: That's actually {}.".format(self.correct.first_last()))
            msg.setWindowTitle("Error")
        msg.exec_()
        print("Clicked: {}".format(button_index))
        print("Num Labels: {}".format(self.num_labels()))
        self.setup_problem()

    def run(self):
        self.window.show()
        self.app.exec_()


if __name__ == "__main__":
    path = "F2019-28-Aug"
    rel_path = ".."
    students = []
    with open(os.path.join(rel_path, "{}.html".format(path))) as fp:
        doc = BeautifulSoup(fp, "html.parser")
    for table in doc.find_all("tbody"):
        rows = [t for t in table.children if t.name == "tr"]
        header_cells = rows[0].find_all("td")
        if len(header_cells) != 2:
            continue
        if header_cells[1].get_text().strip() != "Student Information":
            continue
        for row in rows[1:]:
            student = Student.from_row(row, rel_path)
            students.append(student)

    with connect_db() as db:
        window = MainWindow(students, db)
        window.run()
