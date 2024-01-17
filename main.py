from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QFileDialog, QComboBox, QVBoxLayout, QWidget, QMessageBox, QLabel, QHBoxLayout, QTextEdit
from PySide6.QtCore import QThread, Signal
import whisper
import time
import sys
import os

MODELS = ["tiny","base (2x time)","small (5x time)","medium (16x time)","large (32x time)"]
LANGUAGES = ["Afrikaans","Albanian","Amharic","Arabic","Armenian","Assamese","Azerbaijani","Bashkir","Basque","Belarusian","Bengali","Bosnian","Breton","Bulgarian","Burmese","Cantonese","Castilian","Catalan","Chinese","Croatian","Czech","Danish","Dutch","English","Estonian","Faroese","Finnish","Flemish","French","Galician","Georgian","German","Greek","Gujarati","Haitian","Haitian Creole","Hausa","Hawaiian","Hebrew","Hindi","Hungarian","Icelandic","Indonesian","Italian","Japanese","Javanese","Kannada","Kazakh","Khmer","Korean","Lao","Latin","Latvian","Letzeburgesch","Lingala","Lithuanian","Luxembourgish","Macedonian","Malagasy","Malay","Malayalam","Maltese","Mandarin","Maori","Marathi","Moldavian","Moldovan","Mongolian","Myanmar","Nepali","Norwegian","Nynorsk","Occitan","Panjabi","Pashto","Persian","Polish","Portuguese","Punjabi","Pushto","Romanian","Russian","Sanskrit","Serbian","Shona","Sindhi","Sinhala","Sinhalese","Slovak","Slovenian","Somali","Spanish","Sundanese","Swahili","Swedish","Tagalog","Tajik","Tamil","Tatar","Telugu","Thai","Tibetan","Turkish","Turkmen","Ukrainian","Urdu","Uzbek","Valencian","Vietnamese","Welsh","Yiddish","Yoruba"]

def write_txt(segments, output_file):
    with open(output_file, 'w') as f:
        for segment in segments:
            text = segment['text']
            f.write(text + '\n')

def write_srt(segments, output_file):
    with open(output_file, 'w') as f:
        for i, segment in enumerate(segments, start=1):
            start_time = float(segment['start'])
            end_time = float(segment['end'])
            text = segment['text']

            start_time_srt = "{:02}:{:02}:{:02},{:03}".format(int(start_time // 3600), int((start_time % 3600) // 60), int(start_time % 60), int((start_time % 1) * 1000))
            end_time_srt = "{:02}:{:02}:{:02},{:03}".format(int(end_time // 3600), int((end_time % 3600) // 60), int(end_time % 60), int((end_time % 1) * 1000))

            f.write(f"{i}\n")
            f.write(f"{start_time_srt} --> {end_time_srt}\n")
            f.write(f"{text}\n\n")

class ASRThread(QThread):
    progress_signal = Signal(str)
    error_signal = Signal(str)

    def __init__(self, selected_file, selected_model, selected_language, output_location):
        super(ASRThread, self).__init__()
        self.selected_file = selected_file
        self.selected_model = selected_model
        self.selected_language = selected_language
        self.output_location = output_location

    def run(self):
        try:
            self.progress_signal.emit("Loading model...")
            model = whisper.load_model(self.selected_model)

            start_time = time.time()
            start_time_str = time.strftime("%H:%M:%S", time.localtime(start_time))
            self.progress_signal.emit(f"Transcribing... (This may take a long time; started at {start_time_str})")
            result = model.transcribe(self.selected_file, word_timestamps=True, language=self.selected_language)

            write_srt(result['segments'], os.path.join(self.output_location, 'output.srt'))
            write_txt(result['segments'], os.path.join(self.output_location, 'output.txt'))

            end_time = time.time()
            time_taken = end_time - start_time
            self.progress_signal.emit(f"Done. Time taken: {time_taken:.2f} seconds.")
        except Exception as e:
            self.error_signal.emit(str(e))
            self.progress_signal.emit("Error occurred.")

class ErrorWindow(QMainWindow):
    def __init__(self, error_message):
        super(ErrorWindow, self).__init__()
        self.setWindowTitle("Error")
        self.error_display = QTextEdit()
        self.error_display.setReadOnly(True)
        self.error_display.setText(error_message)
        self.setCentralWidget(self.error_display)

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        self.setWindowTitle("Whisper Transcription App")

        self.button = QPushButton("Choose Media File")
        self.button.clicked.connect(self.open_file_dialog)

        self.file_label = QLabel("No file chosen")
        
        self.clear_button = QPushButton("Clear File")
        self.clear_button.clicked.connect(self.clear_file)

        self.output_button = QPushButton("Choose Output Location")  # New button for choosing output location
        self.output_button.clicked.connect(self.open_output_dialog)  # Connect to new method

        self.output_label = QLabel("No output location chosen")  # New label for displaying chosen output location

        self.model_label = QLabel("Model:")
        self.model_box = QComboBox()
        self.model_box.addItems(MODELS)

        self.language_label = QLabel("Language:")
        self.language_box = QComboBox()
        self.language_box.addItems(LANGUAGES)
        self.language_box.setCurrentText("Chinese")

        self.run_button = QPushButton("Transcribe")
        self.run_button.clicked.connect(self.run_asr)

        self.progress_label = QLabel("")

        file_layout = QHBoxLayout()
        file_layout.addWidget(self.button)
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(self.clear_button)

        output_layout = QHBoxLayout()  # New layout for output location
        output_layout.addWidget(self.output_button)
        output_layout.addWidget(self.output_label)

        model_layout = QHBoxLayout()
        model_layout.addWidget(self.model_label)
        model_layout.addWidget(self.model_box)

        language_layout = QHBoxLayout()
        language_layout.addWidget(self.language_label)
        language_layout.addWidget(self.language_box)

        layout = QVBoxLayout()
        layout.addLayout(file_layout)
        layout.addLayout(output_layout)  # Add new layout to main layout
        layout.addLayout(model_layout)
        layout.addLayout(language_layout)
        layout.addWidget(self.run_button)
        layout.addWidget(self.progress_label)

        widget = QWidget()
        widget.setLayout(layout)

        self.setCentralWidget(widget)

    def error_dialog(self, e):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText("Error")
        msg.setInformativeText(str(e))
        msg.setWindowTitle("Error")
        msg.exec_()

    def open_file_dialog(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open audio file", "", "Audio Files (*)")
        if file_name:
            self.selected_file = file_name
            self.file_label.setText(file_name)

    def open_output_dialog(self):  # New method for opening output location dialog
        dir_name = QFileDialog.getExistingDirectory(self, "Open output location", "")
        if dir_name:
            self.output_location = dir_name
            self.output_label.setText(dir_name)

    def clear_file(self):
        self.selected_file = None
        self.file_label.setText("No file chosen")

    def update_progress(self, progress):
        self.progress_label.setText(progress)

    def show_error(self, error_message):
        self.error_window = ErrorWindow(error_message)
        self.error_window.show()

    def run_asr(self):
        try:
            if not hasattr(self, 'selected_file') or not os.path.exists(self.selected_file):
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Critical)
                msg.setText("Error")
                msg.setInformativeText('Please select a valid file before running the transcription')
                msg.setWindowTitle("Error")
                msg.exec_()
                return

            if not hasattr(self, 'output_location') or not os.path.exists(self.output_location):
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Critical)
                msg.setText("Error")
                msg.setInformativeText('Please select a valid output location before running the transcription')
                msg.setWindowTitle("Error")
                msg.exec_()
                return

            selected_model = self.model_box.currentText()
            selected_language = self.language_box.currentText()
            self.asr_thread = ASRThread(self.selected_file, selected_model, selected_language, self.output_location)
            self.asr_thread.progress_signal.connect(self.update_progress)
            self.asr_thread.error_signal.connect(self.show_error) 
            self.asr_thread.finished.connect(self.asr_finished)
            self.asr_thread.start()
            self.run_button.setEnabled(False)
        
        except Exception as e:
            self.error_window = ErrorWindow(str(e))
            self.error_window.show()
            self.progress_label.setText("Error occurred.")

    def asr_finished(self):
        self.run_button.setEnabled(True)

app = QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec_()
