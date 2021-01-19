from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QPlainTextEdit,
                             QHBoxLayout, QVBoxLayout, QWidget, QInputDialog, QLineEdit, QMessageBox,
                             QRadioButton, QButtonGroup, QCheckBox)
from PyQt5.QtCore import QProcess
from PyQt5.QtGui import QFont
import sys
# import image_watchdog
from measurement_directory import measurement_directory, todays_measurements, parse
import os
import pickle

analysis_modes = {'ycam': 1, 'zcam dual': 1, 'zcam triple': 3, 'testing': 1}
analysis_shorthand = {'ycam': 'y', 'zcam dual': 'zd', 'zcam triple': 'zt'}


def _suggest_runfolder_path(appendrun, runname_str=None, basepath=''):
    run_folders = todays_measurements(basepath=basepath)
    runs = {}
    for directory in run_folders:
        result = parse.parse('run{}_{}', directory)
        run_idx, run_name = int(result[0]), result[1]
        runs[run_idx] = run_name
    if len(runs) == 0:
        print('first run of the day! run_idx: 0')
        measurement_name = 'run0_' + runname_str
    else:
        last_run_idx = sorted(runs.keys())[-1]
        print('last run: run{idx}_{name} ...'.format(
            idx=str(last_run_idx), name=runs[last_run_idx]))
        if not appendrun:
            if runname_str is None:
                raise ValueError('Need run name for new run.')
            new_run_idx = last_run_idx + 1
            measurement_name = 'run{idx}_'.format(
                idx=str(new_run_idx)) + runname_str
        else:
            measurement_name = 'run{idx}_{name}'.format(
                idx=str(last_run_idx), name=runs[last_run_idx])
    runfolder_path = measurement_directory(
        measurement_name=measurement_name, warn=False)
    return os.path.abspath(runfolder_path)

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle('Enrico live launcher')
        self.analysisModeBtn_y = QRadioButton('ycam')
        self.analysisModeBtn_zt = QRadioButton('zcam dual')
        self.analysisModeBtn_zd = QRadioButton('zcam triple')
        self.analysisBtns = QButtonGroup()
        for btn in [self.analysisModeBtn_y, self.analysisModeBtn_zd, self.analysisModeBtn_zt]:
            self.analysisBtns.addButton(btn)
        self.btn = QPushButton("START")
        self.discard_box = QCheckBox('Discard images after analysis')
        self.btn.pressed.connect(self.start_process)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setFont(QFont("Arial", 14))

        self.text2 = QPlainTextEdit()
        self.text2.setReadOnly(True)
        self.text2.setFont(QFont("Arial", 14))

        l = QVBoxLayout()
        for btn in [self.analysisModeBtn_y, self.analysisModeBtn_zd, self.analysisModeBtn_zt]:
            l.addWidget(btn)
        l.addWidget(self.discard_box)
        l.addWidget(self.btn)
        l.addWidget(self.text)
        l.addWidget(self.text2)

        w = QWidget()
        w.setLayout(l)

        self.setCentralWidget(w)

    def start_process(self):
        if self.btn.text() == "START":
            self.text.clear()
            self.text2.clear()
            if len(todays_measurements()) > 0:
                last_run_name = todays_measurements()[-1]
            else:
                last_run_name = 'no runs yet. First run of the day!'
            buttonReply = QMessageBox.question(
                self, '', "Last run name: " + last_run_name + "\nStart new run?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if buttonReply == QMessageBox.Yes:
                text, okPressed = QInputDialog.getText(
                    self, '', 'Name your run: ', QLineEdit.Normal, "")

                if okPressed:
                    self.runfolder_path = _suggest_runfolder_path(
                        appendrun=False, runname_str=text)
            elif buttonReply == QMessageBox.No:
                self.runfolder_path = _suggest_runfolder_path(appendrun=True)
            self.text.appendPlainText(
                'Moving images to ' + self.runfolder_path)
            # Keep a reference to the QProcess (e.g. on self) while it's running.
            self.ImageWatchdogProcess = QProcess()
            self.ImageWatchdogProcess.readyReadStandardOutput.connect(
                self.generate_stdout_handler(self.ImageWatchdogProcess, self.text))
            self.ImageWatchdogProcess.readyReadStandardError.connect(
                self.generate_stderr_handler(self.ImageWatchdogProcess, self.text))
            # self.ImageWatchdogProcess.stateChanged.connect(self.handle_state)
            # self.ImageWatchdogProcess.finished.connect(self.process_finished)
            for btn in [self.analysisModeBtn_y, self.analysisModeBtn_zd, self.analysisModeBtn_zt]:
                if btn.isChecked():
                    analysisMode_str = btn.text()
                    self.text2.appendPlainText(
                        analysisMode_str + ' analysis mode selected.')
            if self.discard_box.isChecked():
                self.text2.appendPlainText('DISCARDING IMAGES AFTER ANALYSIS.')
            self.AnalysisProcess = QProcess()
            self.AnalysisProcess.readyReadStandardOutput.connect(
                self.generate_stdout_handler(self.AnalysisProcess, self.text2))
            self.AnalysisProcess.readyReadStandardError.connect(
                self.generate_stderr_handler(self.AnalysisProcess, self.text2))

            # self.ImageWatchdogProcess.start("python", ['dummy_printer.py'])
            # self.AnalysisProcess.start("python", ['dummy_printer.py'])
            self.ImageWatchdogProcess.start("python", [
                                            'image_watchdog.py', self.runfolder_path, str(analysis_modes[analysisMode_str])])
            self.AnalysisProcess.start(
                "python", ['analysis_loggerOOP.py', analysis_shorthand[analysisMode_str], self.runfolder_path, str(not self.discard_box.isChecked())])

        else:
            self.ImageWatchdogProcess.kill()
            self.AnalysisProcess.kill()
            del self.ImageWatchdogProcess
            del self.AnalysisProcess
            # self.export_params_csv()
            print('STOPPED')
        self.btn.setText("STOP" if self.btn.text() == "START" else "START")

    def generate_stderr_handler(self, process, text):
        def handle_stderr():
            data = process.readAllStandardError()
            stderr = bytes(data).decode("utf8")
            text.appendPlainText(stderr)
        return handle_stderr

    def generate_stdout_handler(self, process, text):
        def handle_stdout():
            data = process.readAllStandardOutput()
            stdout = bytes(data).decode("utf8")
            text.appendPlainText(stdout)
        return handle_stdout

    def export_params_csv(self):
        with open(os.path.join(self.runfolder_path, 'analysisLogger.pkl'), 'rb') as file:
            myAnalysisLogger = pickle.load(file)
        myAnalysisLogger.export_params_csv()

    # def handle_state(self, state):
    #     states = {
    #         QProcess.NotRunning: 'Not running',
    #         QProcess.Starting: 'Starting',
    #         QProcess.Running: 'Running',
    #     }
    #     state_name = states[state]
    #     # self.text2.appendPlainText(f"State changed: {state_name}")

    # def process_finished(self):
    #     self.text.appendPlainText("Process finished.")
    #     # self.text.clear()
    #     self.p = None


app = QApplication(sys.argv)
app.setStyle('Fusion')

w = MainWindow()
w.show()

app.exec_()
