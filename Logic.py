from PyQt5.QtWidgets import QMainWindow
from PyQt5 import QtWidgets, QtCore
from PyQt5 import QtGui
import sys, os
import tempfile
import numpy as np #We import this in order to define the angle parameters below with pi!
from PyQt5.QtCore import QTimer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

#Import the generated code from the .py file that describes the user interface.
from Ui_Design import Ui_MainWindow
from ISatQuLLoS import Simulation
######################################################################################################################################################
######################################################################################################################################################

# Define a PrintRedirector class to redirect output to a PyQt signal
class PrintRedirector(QtCore.QObject):
    newText = QtCore.pyqtSignal(str) #This is to create a signal to update the text on the interface.
    #stop_signal = QtCore.pyqtSignal()

    def write(self, text):
        self.newText.emit(str(text))

    def flush(self): 
        #this does nothing, but solves an issue in regards to an attribute error for the print statements on the interface.
        pass

# Define the main application logic class
class Logic(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self._configure_responsive_ui()
        self.simulation = Simulation() #Create an instance of the Simulation class from the simulations module in here.
        self.setup_sliders()
        self.fig3D = None  # Store the plot object
        self.views = []  # Keep track of created QWebEngineView instances
        self.plot_widgets = {}  # Dictionary to store plot widgets
        self._plotly_view = None
        self._plotly_ready = False
        self._plotly_html_loaded = False
        self._plotly_load_connected = False
        self._pending_3d_payload_json = None
        self._pending_3d_trace_payload_json = None
        self._plotly_retry_count = 0
        self._plotly_flush_scheduled = False
        self._default_3d_parameters = (530, 720, 180, 72, 1)
        self._last_simulation_3d_parameters = None
        self._plot_status_text = "Default parameters"
        self._plot_status_detail = "Initial reference view"
        self._max_3d_orbit_samples = 360

        #Flags:
        self.IsFirstSimulation = True #Set first simulation called flag to True.
        self.isCalled_3D_Plot = False #Set standalone 3D Plot flag to False.
        self.was_3D_Plot_created = False #Flag to check if a 3D plot was made either from running the simulations or by the standalone "Called_3D_Plot" maker.

        self.file_path = ''
        self.file_name = ''
        self.plot3D_orbits = None
        self.fig = None

        ############### Define the parameters as instance variables ###############
        self.H1 = 530
        self.H2 = 720
        self.α = 180
        self.β = 72
        self.n = 1
        self.r_Tx = 0.05
        self.r_Rx = 0.15
        self.r_Tx_min = 0
        self.r_Rx_min = 0
        self.λ0 = 300
        self.intLoss = 3
        self.I_Tx_Function0 = "I_Tx"  ##☺
        self.K = 1
        self.t_slice = 20
        self.path = "C:/Users/"+os.getlogin()+"/Desktop/" ##☺
        ###########################################################################

        #Below we set the initial vlaues that show in the lineEdits next to the sliders:
        self._sync_visualize_controls_from_parameters()

        ###########################################################################


        #Here we connect all buttons and functionalities to the respective methods.
        self.button1.clicked.connect(self.show_acknowledgement)
        self.button2.clicked.connect(self.show_project_link_placeholder)
        
        self.button_updateParameters.clicked.connect(lambda: self.update_Parameters())
        self.button_storeParameters.clicked.connect(lambda: self.store_Parameters())
        self.button_selectParametersFile.clicked.connect(lambda: self.select_Parameters_File())
        self.button_loadParameters.clicked.connect(lambda: self.import_Parameters())
        self.button_selectOutput.clicked.connect(lambda: self.select_Output())
        self.button_runSimulation.clicked.connect(lambda: self.run_simulation())
        self.button_stopSimulation.clicked.connect(lambda: self.stop_simulation())

        self.button_call_3D_plot.clicked.connect(lambda: self.call_3D_plot())

        #Create a PrintRedirector instance to redirect the output of the print function
        #Connect the progressUpdate signal from the ISatQuLLoS module.
        self.print_redirector = PrintRedirector()
        self.print_redirector.newText.connect(self.append_text)
        sys.stdout = self.print_redirector
        
        self.simulation.progressUpdated.connect(self.update_progress_bar)
        #self.simulation.DataStatus.connect(self.run_simulation)

        #Allow the user to open the link in the About Section by clicking the link embedded text.
        self.textBrowser.setOpenLinks(False)
        self.textBrowser.anchorClicked.connect(self.handleLinkClicked)

        self._load_default_3d_plot()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_responsive_scale()
        self._update_parameter_image_view()
        self._request_3d_plot_resize()

    def select_Parameters_File(self):
        self.file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select .TXT parameters file") #note that the second return "_" is the selected filters, not the file name.
        self.file_name = os.path.basename(self.file_path)
        if self.file_path:
            self.lineEdit_importParameters.setText(self.file_path) #This is to show the path selected on the GUI.

    def import_Parameters(self):
        file_path = self.file_path
        file_name = self.file_name

        if file_path and file_name:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    #parameters_list = [text_H1, text_H2, text_r_Tx, text_r_Rx, text_α, text_β, text_n, text_λ0, text_r_Tx_min, text_r_Rx_min, text_t_slice, text_K, text_intLoss, text_path]
                    parameters_list = [line.rstrip("\r\n") for line in file.readlines()]
            except OSError as error:
                self._show_message("Failed to load parameters", f"The selected parameter file could not be read:\n\n{error}")
                return

            while parameters_list and parameters_list[-1] == "":
                parameters_list.pop()

            minimum_parameter_count = 13
            maximum_parameter_count = 14
            if len(parameters_list) not in (minimum_parameter_count, maximum_parameter_count):
                message = (
                    f"The selected parameter file contains {len(parameters_list)} line(s), "
                    f"but {minimum_parameter_count} or {maximum_parameter_count} are required."
                )
                if len(parameters_list) == 1:
                    message += (
                        "\n\nThis file may have been saved without line breaks by an older version. "
                        "Please save the parameters again using the updated Save Parameters button."
                    )
                self._show_message("Invalid parameter file", message)
                return

            # Assign each line to a variable and write it in the respective lineEdits on the interface.
            self.lineEdit_H1.setText(parameters_list[0])
            self.lineEdit_H2.setText(parameters_list[1])
            self.lineEdit_d_T.setText(parameters_list[2])
            self.lineEdit_d_R.setText(parameters_list[3])
            self.lineEdit_alpha.setText(parameters_list[4])
            self.lineEdit_beta.setText(parameters_list[5])
            self.lineEdit_n.setText(parameters_list[6])
            self.lineEdit_wavelength.setText(parameters_list[7])
            self.lineEdit_r_Tx_min.setText(parameters_list[8])
            self.lineEdit_r_Rx_min.setText(parameters_list[9])
            self.lineEdit_t_slice.setText(parameters_list[10])
            self.lineEdit_K.setText(parameters_list[11])
            self.lineEdit_intLoss.setText(parameters_list[12])
            if len(parameters_list) == maximum_parameter_count:
                self.lineEdit_selectOutput.setText(parameters_list[13])
            else:
                self.lineEdit_selectOutput.clear()

            print(f"Parameter file '{file_name}' imported successfully.")
        else:
            self._show_message("No parameter file selected", "Please select a parameter file before loading.")

    def store_Parameters(self):
        #Below we prompt the user to give a name to the file to be created as well as selecting the 
        #diretory where the file will be saved, by leaving an empty string '""' for the directory path argument.
        file_name, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save File", "", "Text Files (*.txt)")

        text_H1 = str(self.lineEdit_H1.text())
        text_H2 = str(self.lineEdit_H2.text())
        text_α = str(self.lineEdit_alpha.text())
        text_β = str(self.lineEdit_beta.text())
        text_n = str(self.lineEdit_n.text())
        text_r_Tx = str(self.lineEdit_d_T.text())
        text_r_Rx = str(self.lineEdit_d_R.text())
        text_r_Tx_min = str(self.lineEdit_r_Tx_min.text())
        text_r_Rx_min = str(self.lineEdit_r_Rx_min.text())
        text_λ0 = str(self.lineEdit_wavelength.text())
        text_intLoss = str(self.lineEdit_intLoss.text())
        text_K = str(self.lineEdit_K.text())
        text_t_slice = str(self.lineEdit_t_slice.text())
        text_path = str(self.lineEdit_selectOutput.text()).strip()

        text_list = [text_H1, text_H2, text_r_Tx, text_r_Rx, text_α, text_β, text_n, text_λ0, text_r_Tx_min, text_r_Rx_min, text_t_slice, text_K, text_intLoss]
        if text_path:
            text_list.append(text_path)
        if file_name:
            try:
                with open(file_name, 'w', encoding='utf-8') as file:
                    file.write("\n".join(text_list))
                    file.write("\n")
            except OSError as error:
                self._show_message("Failed to save parameters", f"The parameter file could not be saved:\n\n{error}")
                return
            print(f"Parameter file created successfully under '{file_name}'.")

    def _show_message(self, title, text, icon=QtWidgets.QMessageBox.Warning, rich_text=False):
        message_box = QtWidgets.QMessageBox(self)
        message_box.setIcon(icon)
        message_box.setWindowTitle(title)
        message_box.setTextFormat(QtCore.Qt.RichText if rich_text else QtCore.Qt.PlainText)
        message_box.setText(text)
        message_box.exec_()

    def _confirm_default_output_folder(self, text):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Output folder not selected")
        dialog.setModal(True)
        dialog.setMinimumWidth(460)

        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(12)

        content_layout = QtWidgets.QHBoxLayout()
        content_layout.setSpacing(12)

        icon_label = QtWidgets.QLabel(dialog)
        icon = self.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxInformation)
        icon_label.setPixmap(icon.pixmap(32, 32))
        icon_label.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
        content_layout.addWidget(icon_label, 0, QtCore.Qt.AlignTop)

        text_layout = QtWidgets.QVBoxLayout()
        message_label = QtWidgets.QLabel(text, dialog)
        message_label.setWordWrap(True)
        question_label = QtWidgets.QLabel("Do you want to continue with this output folder?", dialog)
        question_label.setWordWrap(True)
        text_layout.addWidget(message_label)
        text_layout.addWidget(question_label)
        content_layout.addLayout(text_layout, 1)
        layout.addLayout(content_layout)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch(1)
        cancel_button = QtWidgets.QPushButton("Cancel", dialog)
        continue_button = QtWidgets.QPushButton("Continue", dialog)
        continue_button.setStyleSheet("""
            QPushButton {
                background-color: #f1f3f5;
                border: 1px solid #c8d0d8;
                border-radius: 5px;
                padding: 5px 14px;
            }
        """)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #eef6ff;
                border: 1px solid #bdd7f2;
                border-radius: 5px;
                padding: 5px 14px;
            }
        """)
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(continue_button)
        layout.addLayout(button_layout)

        cancel_button.clicked.connect(dialog.reject)
        continue_button.clicked.connect(dialog.accept)
        return dialog.exec_() == QtWidgets.QDialog.Accepted

    def _aperture_validation_errors(self, r_Tx, r_Rx, r_Tx_min, r_Rx_min):
        aperture_errors = []
        r_tx = "r<sub>Tx</sub>"
        r_rx = "r<sub>Rx</sub>"
        r_tx_min = "r<sub>Tx</sub><sup>min</sup>"
        r_rx_min = "r<sub>Rx</sub><sup>min</sup>"
        if not all(np.isfinite(value) for value in (r_Tx, r_Rx, r_Tx_min, r_Rx_min)):
            aperture_errors.append("All aperture values must be finite numbers.")
        if r_Tx <= 0:
            aperture_errors.append(f"{r_tx} must be greater than 0 m.")
        if r_Rx <= 0:
            aperture_errors.append(f"{r_rx} must be greater than 0 m.")
        if r_Tx_min < 0:
            aperture_errors.append(f"{r_tx_min} must be greater than or equal to 0 m.")
        if r_Rx_min < 0:
            aperture_errors.append(f"{r_rx_min} must be greater than or equal to 0 m.")
        if r_Tx > 0 and r_Tx_min >= r_Tx:
            aperture_errors.append(f"{r_tx_min} must be smaller than {r_tx}.")
        if r_Rx > 0 and r_Rx_min >= r_Rx:
            aperture_errors.append(f"{r_rx_min} must be smaller than {r_rx}.")
        return aperture_errors

    def update_Parameters(self):
        #We create a list containing all parameters inputted.
        parameters_List = [self.lineEdit_H1.text(), self.lineEdit_H2.text(), self.lineEdit_alpha.text(), self.lineEdit_beta.text(), self.lineEdit_n.text(), self.lineEdit_d_T.text(), self.lineEdit_d_R.text(), self.lineEdit_r_Tx_min.text(), self.lineEdit_r_Rx_min.text(), self.lineEdit_wavelength.text(), self.lineEdit_intLoss.text(), self.lineEdit_K.text(), self.lineEdit_t_slice.text()]

        #Below we check that the user has filled in all required parameters before storing them.
        for i in range(len(parameters_List)):
            if not parameters_List[i]:
                self._show_message("ERROR: Missing input.", "Please fill in all required parameters.")
                return
            else:
                pass

        try:
            H1 = float(self.lineEdit_H1.text())
            H2 = float(self.lineEdit_H2.text())
            α = float(self.lineEdit_alpha.text())
            β = float(self.lineEdit_beta.text())
            n = float(self.lineEdit_n.text())
            r_Tx = float(self.lineEdit_d_T.text())
            r_Rx = float(self.lineEdit_d_R.text())
            r_Tx_min = float(self.lineEdit_r_Tx_min.text())
            r_Rx_min = float(self.lineEdit_r_Rx_min.text())
            λ0 = float(self.lineEdit_wavelength.text())
            intLoss = float(self.lineEdit_intLoss.text())
            K = float(self.lineEdit_K.text())
            t_slice = float(self.lineEdit_t_slice.text())
        except ValueError:
            self._show_message("Invalid parameter input", "Please check that all parameter fields contain valid numeric values.")
            return

        aperture_errors = self._aperture_validation_errors(r_Tx, r_Rx, r_Tx_min, r_Rx_min)
        if aperture_errors:
            self._show_message(
                "Invalid aperture parameters",
                "<p>Please check the aperture parameters:</p>"
                "<ul>" + "".join(f"<li>{error}</li>" for error in aperture_errors) + "</ul>",
                rich_text=True,
            )
            return

        self.H1 = H1
        self.H2 = H2
        self.α = α
        self.β = β
        self.n = n
        self.r_Tx = r_Tx
        self.r_Rx = r_Rx
        self.r_Tx_min = r_Tx_min
        self.r_Rx_min = r_Rx_min
        self.λ0 = λ0
        self.intLoss = intLoss
        self.K = K
        self.t_slice = t_slice
        self.path = str(self.lineEdit_selectOutput.text())
        self._sync_visualize_controls_from_parameters()
        print("** Parameter list updated.")

    def select_Output(self):
        self.folder_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select the desired output folder") #note that the second return "_" is the selected filters, not the file name.
        self.folder_name = os.path.basename(self.folder_path)
        if self.folder_path:
            self.path = self.folder_path #If "self.folder_path" was selected, set output folder path "self.path" to "self.folder_path".
            self.lineEdit_selectOutput.setText(self.folder_path) #This is to show the path selected on the GUI.
            print(f"Output folder '{self.folder_name}' selected.")

    def _default_output_folder(self):
        if getattr(sys, "frozen", False):
            return os.path.dirname(os.path.abspath(sys.executable))
        return BASE_DIR

    def _validated_output_folder(self):
        output_folder = str(self.lineEdit_selectOutput.text()).strip()
        warning_message = ""
        if not output_folder:
            output_folder = self._default_output_folder()
            warning_message = (
                "No output folder was selected.\n\n"
                "The Time - Loss.csv file will be saved in:\n"
                f"{output_folder}"
            )
        folder_description = "default output folder" if warning_message else "selected output folder"

        output_folder = os.path.abspath(os.path.expanduser(output_folder))
        if not os.path.isdir(output_folder):
            return None, f"The {folder_description} does not exist:\n{output_folder}", ""

        try:
            with tempfile.NamedTemporaryFile(prefix="isatqullos_write_test_", suffix=".tmp", dir=output_folder, delete=True):
                pass
        except OSError as error:
            return None, f"The {folder_description} is not writable:\n{output_folder}\n\n{error}", ""

        return output_folder, "", warning_message

    @QtCore.pyqtSlot() #Decorator needed to send signal to run the simulations once logic file is instructed to do so by the user.
    def run_simulation(self):
        output_folder, output_error, output_warning = self._validated_output_folder()
        if output_error:
            self._show_message("Invalid output folder", output_error)
            self.progressBar.setFormat("%p%")
            self.update_progress_bar(0)
            return
        if output_warning and not self._confirm_default_output_folder(output_warning):
            self.progressBar.setFormat("%p%")
            self.update_progress_bar(0)
            return

        self.path = output_folder
        if not output_warning:
            self.lineEdit_selectOutput.setText(output_folder)

        #Set is_running flag to True, or stop_simulation to false.
        self.simulation.stop = False
        self.progressBar.setFormat("Running... %p%")
        self.update_progress_bar(0)
        self.button_runSimulation.setEnabled(False)
        self.button_stopSimulation.setEnabled(True)

        #Call the main function from the ISatQuLLoS module with the input parameters.
        #We set it equals to a list of figures "figs" that are returned from the main() method.
        #self.simulation.main(self, self.H1, self.H2, self.α, self.β, self.n, self.r_Tx, self.r_Rx, self.r_Tx_min, self.r_Rx_min, self.λ0, self.intLoss, self.I_Tx_Function0, self.K, self.t_slice, self.path).progressUpdated.connect(self.update_progress_bar)
        #The first figure in the figs list, is the 3D plot.
        try:
            figs = self.simulation.main(self.H1, self.H2, self.α, self.β, self.n, self.r_Tx, self.r_Rx, self.r_Tx_min, self.r_Rx_min, self.λ0, self.intLoss, self.I_Tx_Function0, self.K, self.t_slice, self.path)

            if self.simulation.stop == False:
                self._last_simulation_3d_parameters = (self.H1, self.H2, self.α, self.β, self.n)
                # Update the attribute with the 3D plot
                self.display_3D_plot_trace_update(
                    figs[0],
                    "Last simulation parameters",
                    "Plot matches the most recent simulation run",
                )
                self._sync_visualize_controls_from_parameters()

                #If not enough data was available, the list will only contain 2 plots.
                #Here we handle the exception locally by checking the length of the list (instead of sending signals from the sim module to let us know "if NoData==True").
                if len(figs) == 7: #Could also have written: "if len(figs) > 2:"
                    #Convert the figures to QPixmap objects and display them in the QGraphicsView widgets:
                    self.display_figure_in_QGraphicsView(figs[1], "graphicsView_plot0")
                    self.display_figure_in_QGraphicsView(figs[2], "graphicsView_plot1")
                    self.display_figure_in_QGraphicsView(figs[3], "graphicsView_plot2")
                    self.display_figure_in_QGraphicsView(figs[4], "graphicsView_plot3")

                self.update_progress_bar(100)
                self.progressBar.setFormat("Complete - %p%")
            else:
                self.progressBar.setFormat("Stopped at %p%")
        finally:
            self.button_runSimulation.setEnabled(True)

        #Now set "first simulation" flag to False.
        self.IsFirstSimulation = False

        #Now set "was 3D plot created" flag to True.
        self.was_3D_Plot_created = True

    def stop_simulation(self):
        self.simulation.stop = True

    #Method to connect the 'valueChanged' signals of the sliders to the update_3D_plot slot.
    def setup_sliders(self):
        self._is_updating_sliders = False
        self._slider_plot_update_timer = QTimer(self)
        self._slider_plot_update_timer.setSingleShot(True)
        self._slider_plot_update_timer.timeout.connect(self.update_3D_plot)

        slider_specs = (
            (self.slider_H1, self.lineEdit_H1Value, 10, 100),
            (self.slider_H2, self.lineEdit_H2Value, 10, 100),
            (self.slider_Alpha, self.lineEdit_alphaValue, 1, 15),
            (self.slider_Beta, self.lineEdit_betaValue, 1, 20),
        )
        self._visualize_value_inputs = {}
        for slider, value_edit, step, tick_interval in slider_specs:
            slider.setSingleStep(step)
            slider.setPageStep(max(step * 10, tick_interval))
            slider.setTickInterval(tick_interval)
            value_edit.setReadOnly(False)
            value_edit.setValidator(QtGui.QIntValidator(slider.minimum(), slider.maximum(), self))
            value_edit.setToolTip("Type a value directly, then press Enter or leave the field.")
            value_edit.editingFinished.connect(
                lambda slider=slider, value_edit=value_edit: self._apply_visualize_value_edit(slider, value_edit)
            )
            self._visualize_value_inputs[value_edit] = slider

        #This slot will be called whenever any of the sliders' values change by the specified step size.
        #Connect the 'sliderReleased' signal of the sliders to the update_3D_plot slot
        self.slider_H1.sliderReleased.connect(self._run_scheduled_3d_plot_update)
        self.slider_H2.sliderReleased.connect(self._run_scheduled_3d_plot_update)
        self.slider_Alpha.sliderReleased.connect(self._run_scheduled_3d_plot_update)
        self.slider_Beta.sliderReleased.connect(self._run_scheduled_3d_plot_update)

        # Connect the 'valueChanged' signal of the sliders to a custom slot
        self.slider_H1.valueChanged.connect(lambda value: self.handle_slider_value_changed(value, self.slider_H1))
        self.slider_H2.valueChanged.connect(lambda value: self.handle_slider_value_changed(value, self.slider_H2))
        self.slider_Alpha.valueChanged.connect(lambda value: self.handle_slider_value_changed(value, self.slider_Alpha))
        self.slider_Beta.valueChanged.connect(lambda value: self.handle_slider_value_changed(value, self.slider_Beta))

    def _schedule_3d_plot_update(self):
        if hasattr(self, "_slider_plot_update_timer"):
            self._slider_plot_update_timer.start(75)

    def _run_scheduled_3d_plot_update(self):
        if hasattr(self, "_slider_plot_update_timer"):
            self._slider_plot_update_timer.stop()
        self.update_3D_plot()

    def _bounded_slider_value(self, slider, value, step=None):
        if step is None:
            rounded_value = int(round(float(value)))
        else:
            rounded_value = int(round(float(value) / step) * step)
        return max(slider.minimum(), min(slider.maximum(), rounded_value))

    def _apply_visualize_value_edit(self, slider, value_edit):
        text = value_edit.text().strip()
        if not text:
            value_edit.setText(str(slider.value()))
            return

        try:
            value = int(float(text))
        except ValueError:
            value_edit.setText(str(slider.value()))
            return

        bounded_value = self._bounded_slider_value(slider, value)
        self._is_updating_sliders = True
        try:
            slider.setValue(bounded_value)
        finally:
            self._is_updating_sliders = False

        value_edit.setText(str(bounded_value))
        self.update_3D_plot()

    def _sync_visualize_controls(self, H1, H2, alpha, beta):
        h1_value = self._bounded_slider_value(self.slider_H1, H1)
        h2_value = self._bounded_slider_value(self.slider_H2, H2)
        alpha_value = self._bounded_slider_value(self.slider_Alpha, alpha)
        beta_value = self._bounded_slider_value(self.slider_Beta, beta)

        self._is_updating_sliders = True
        try:
            self.slider_H1.setValue(h1_value)
            self.slider_H2.setValue(h2_value)
            self.slider_Alpha.setValue(alpha_value)
            self.slider_Beta.setValue(beta_value)
        finally:
            self._is_updating_sliders = False

        self.lineEdit_H1Value.setText(str(h1_value))
        self.lineEdit_H2Value.setText(str(h2_value))
        self.lineEdit_alphaValue.setText(str(alpha_value))
        self.lineEdit_betaValue.setText(str(beta_value))

    def _sync_visualize_controls_from_parameters(self):
        self._sync_visualize_controls(self.H1, self.H2, self.α, self.β)

    def handle_slider_value_changed(self, value, slider):
        if getattr(self, "_is_updating_sliders", False):
            return

        value_edit = None
        for edit, mapped_slider in getattr(self, "_visualize_value_inputs", {}).items():
            if mapped_slider is slider:
                value_edit = edit
                break
        if value_edit is not None and not value_edit.hasFocus():
            value_edit.setText(str(self._bounded_slider_value(slider, value)))

        self._schedule_3d_plot_update()

    def update_3D_plot(self):
        if getattr(self, "_is_updating_sliders", False):
            return

        #Set the sliders value to the nearest allowed value
        H1 = self._bounded_slider_value(self.slider_H1, self.slider_H1.value())
        H2 = self._bounded_slider_value(self.slider_H2, self.slider_H2.value())
        alpha = self._bounded_slider_value(self.slider_Alpha, self.slider_Alpha.value())
        beta = self._bounded_slider_value(self.slider_Beta, self.slider_Beta.value())
        #Set the sliders position to the nearest tick mark value
        self._is_updating_sliders = True
        try:
            self.slider_H1.setSliderPosition(H1)
            self.slider_H2.setSliderPosition(H2)
            self.slider_Alpha.setSliderPosition(alpha)
            self.slider_Beta.setSliderPosition(beta)
        finally:
            self._is_updating_sliders = False

        #Here we also update the lineEdit box next to the sliders, to show the current values of the sliders.
        self.lineEdit_H1Value.setText(str(H1))
        self.lineEdit_H2Value.setText(str(H2))
        self.lineEdit_alphaValue.setText(str(alpha))
        self.lineEdit_betaValue.setText(str(beta))


        #Here we call the create3D_Plot method from the sim module with the inserted parameters to make the 3D plot and then 
        #pass the 3D Plot to the display_3D_plot method inside the Logic module to display it onto the interface.
        if self.isCalled_3D_Plot == False and self.was_3D_Plot_created == False:
            pass #fig3D only exists if we create the standalone 3D plot (which must be done before moving the sliders).
            #In this case, we "pass" in that since the plot doesn't exist, moving the slider shoudln't affect anything.
        else:
            G = 6.6743*10**(-11)        #Gravitational constant in SI units
            M = 5.972*10**24            #Mass of the Earth in 'Kg'
            R = 6371*10**3              #Radius of the Earth in 'm'
 
            R1 = R + H1 * 10 ** 3
            R2 = R + H2 * 10 ** 3
            alpha_rad = alpha * (np.pi / 180)
            beta_rad = beta * (np.pi / 180)

            T1 = 2 * np.pi * np.sqrt((R1 ** 3) / (G * M))
            w1 = 2 * np.pi / T1

            T2 = 2 * np.pi * np.sqrt((R2 ** 3) / (G * M))
            w2 = 2 * np.pi / T2

            phi = 2 * np.pi

            if T1>T2:
                T = T1
            elif T2>T1:
                T = T2
            else:
                T = T1 

            t_array = np.arange(0, T, 50)
            theta1_array = w1 * t_array
            theta2_array = w2 * t_array

            x1 = R1 * np.cos(phi) * np.sin(theta1_array - beta_rad)
            y1 = R1 * np.sin(phi) * np.sin(theta1_array - beta_rad)
            z1 = R1 * np.cos(theta1_array - beta_rad)

            x2 = R2 * np.cos(phi - alpha_rad) * np.sin(theta2_array)
            y2 = R2 * np.sin(phi - alpha_rad) * np.sin(theta2_array)
            z2 = R2 * np.cos(theta2_array)

            #Update plot traces (thanks ChatGPT)
            self.fig3D.data[1].x = x1 * 10 ** (-3)
            self.fig3D.data[1].y = y1 * 10 ** (-3)
            self.fig3D.data[1].z = z1 * 10 ** (-3)
            self.fig3D.data[2].x = x2 * 10 ** (-3)
            self.fig3D.data[2].y = y2 * 10 ** (-3)
            self.fig3D.data[2].z = z2 * 10 ** (-3)
            self.fig3D.data[4].x = [x1[0]*10**(-3)]
            self.fig3D.data[4].y = [y1[0]*10**(-3)]
            self.fig3D.data[4].z = [z1[0]*10**(-3)]
            self.fig3D.data[5].x = [x2[0]*10**(-3)]
            self.fig3D.data[5].y = [y2[0]*10**(-3)]
            self.fig3D.data[5].z = [z2[0]*10**(-3)]
            self._set_3d_plot_status("Custom slider view", "Not a completed simulation output")
            self._update_3d_orbit_traces(x1, y1, z1, x2, y2, z2)

    #Method to create the 3D Plot separately from the simulations.
    def call_3D_plot(self):
        #Here we call the create3D_Plot method from the sim module with the inserted parameters to make the 3D plot and then 
        #pass the 3D Plot to the display_3D_plot method inside the Logic module to display it onto the interface.
        if self._last_simulation_3d_parameters is None:
            H1, H2, alpha, beta, n = self._default_3d_parameters
            status_text = "Default parameters"
            status_detail = "No completed simulation yet"
        else:
            H1, H2, alpha, beta, n = self._last_simulation_3d_parameters
            status_text = "Last simulation parameters"
            status_detail = "Plot matches the most recent simulation run"

        self._sync_visualize_controls(H1, H2, alpha, beta)
        self.fig3D = self.simulation.create3D_Plot(H1, H2, alpha, beta, n)
        
        self.display_3D_plot(self.fig3D, status_text, status_detail, force_reload=True)
        print("** 3D Plot created succesfully.")

        #Set standalone 3D Plot flag True AFTER the display_3D_plot method was called once,
        #in order to alert that the standalone 3D plotting method was called.
        self.isCalled_3D_Plot = True

    def _load_default_3d_plot(self):
        H1, H2, alpha, beta, n = self._default_3d_parameters
        self._sync_visualize_controls(H1, H2, alpha, beta)
        self.fig3D = self.simulation.create3D_Plot(H1, H2, alpha, beta, n)
        self.display_3D_plot(self.fig3D, "Default parameters", "Initial reference view")
        self.isCalled_3D_Plot = True

