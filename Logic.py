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
        self.d_T = 0.1
        self.d_R = 0.3
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

        #Force the window to open maximized to the specific screen (no matter their resolution/scaling)
        self.showMaximized()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_responsive_scale()
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
            with open(file_path, 'r') as file:
                #parameters_list = [text_H1, text_H2, text_d_T, text_d_R, text_α, text_β, text_n, text_λ0, text_r_Tx_min, text_r_Rx_min, text_t_slice, text_K, text_intLoss, text_path]
                parameters_list = file.readlines()
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
                self.lineEdit_selectOutput.setText(parameters_list[13])

            print(f"Parameter file '{file_name}' imported successfully.")
        else:
            print("Failed to import the selected file")

    def store_Parameters(self):
        #Below we prompt the user to give a name to the file to be created as well as selecting the 
        #diretory where the file will be saved, by leaving an empty string '""' for the directory path argument.
        file_name, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save File", "", "Text Files (*.txt)")

        text_H1 = str(self.lineEdit_H1.text())
        text_H2 = str(self.lineEdit_H2.text())
        text_α = str(self.lineEdit_alpha.text())
        text_β = str(self.lineEdit_beta.text())
        text_n = str(self.lineEdit_n.text())
        text_d_T = str(self.lineEdit_d_T.text())
        text_d_R = str(self.lineEdit_d_R.text())
        text_r_Tx_min = str(self.lineEdit_r_Tx_min.text())
        text_r_Rx_min = str(self.lineEdit_r_Rx_min.text())
        text_λ0 = str(self.lineEdit_wavelength.text())
        text_intLoss = str(self.lineEdit_intLoss.text())
        text_K = str(self.lineEdit_K.text())
        text_t_slice = str(self.lineEdit_t_slice.text())
        text_path = str(self.lineEdit_selectOutput.text())

        text_list = [text_H1, text_H2, text_d_T, text_d_R, text_α, text_β, text_n, text_λ0, text_r_Tx_min, text_r_Rx_min, text_t_slice, text_K, text_intLoss, text_path]
        if file_name:
            with open(file_name, 'w') as file:
                for i in range(len(text_list)):
                    file.write(text_list[i])
            print(f"Parameter file '{file_name}' created successfully.")

    def update_Parameters(self):
        global H1, H2, α, β, n, d_T, d_R, r_Tx_min, r_Rx_min, λ0, intLoss, I_Tx_Function0, K, t_slice, path

        #We create a list containing all parameters inputted.
        parameters_List = [self.lineEdit_H1.text(), self.lineEdit_H2.text(), self.lineEdit_alpha.text(), self.lineEdit_beta.text(), self.lineEdit_n.text(), self.lineEdit_d_T.text(), self.lineEdit_d_R.text(), self.lineEdit_r_Tx_min.text(), self.lineEdit_r_Rx_min.text(), self.lineEdit_wavelength.text(), self.lineEdit_intLoss.text(), self.lineEdit_K.text(), self.lineEdit_t_slice.text(), self.lineEdit_selectOutput.text()]

        #Below we check that the user has filled in all required parameters before storing them.
        for i in range(len(parameters_List)):
            if not parameters_List[i]:
                QtWidgets.QMessageBox.about(self, "ERROR: Missing input.", "Please fill in all required parameters.")
                return
            else:
                pass

        self.H1 = float(self.lineEdit_H1.text())
        self.H2 = float(self.lineEdit_H2.text())
        self.α = float(self.lineEdit_alpha.text())
        self.β = float(self.lineEdit_beta.text())
        self.n = float(self.lineEdit_n.text())
        self.d_T = float(self.lineEdit_d_T.text())
        self.d_R = float(self.lineEdit_d_R.text())
        self.r_Tx_min = float(self.lineEdit_r_Tx_min.text())
        self.r_Rx_min = float(self.lineEdit_r_Rx_min.text())
        self.λ0 = float(self.lineEdit_wavelength.text())
        self.intLoss = float(self.lineEdit_intLoss.text())
        self.K = float(self.lineEdit_K.text())
        self.t_slice = float(self.lineEdit_t_slice.text())
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

    def _validated_output_folder(self):
        output_folder = str(self.lineEdit_selectOutput.text()).strip()
        if not output_folder:
            return None, "Please select a valid output folder before running the simulations."

        output_folder = os.path.abspath(os.path.expanduser(output_folder))
        if not os.path.isdir(output_folder):
            return None, f"The selected output folder does not exist:\n{output_folder}"

        try:
            with tempfile.NamedTemporaryFile(prefix="isatqullos_write_test_", suffix=".tmp", dir=output_folder, delete=True):
                pass
        except OSError as error:
            return None, f"The selected output folder is not writable:\n{output_folder}\n\n{error}"

        return output_folder, ""

    @QtCore.pyqtSlot() #Decorator needed to send signal to run the simulations once logic file is instructed to do so by the user.
    def run_simulation(self):
        output_folder, output_error = self._validated_output_folder()
        if output_error:
            QtWidgets.QMessageBox.warning(self, "Invalid output folder", output_error)
            self.progressBar.setFormat("%p%")
            self.update_progress_bar(0)
            return

        self.path = output_folder
        self.lineEdit_selectOutput.setText(output_folder)

        #Set is_running flag to True, or stop_simulation to false.
        self.simulation.stop = False
        self.progressBar.setFormat("Running... %p%")
        self.update_progress_bar(0)
        self.button_runSimulation.setEnabled(False)
        self.button_stopSimulation.setEnabled(True)

        #Call the main function from the ISatQuLLoS module with the input parameters.
        #We set it equals to a list of figures "figs" that are returned from the main() method.
        #self.simulation.main(self, self.H1, self.H2, self.α, self.β, self.n, self.d_T, self.d_R, self.r_Tx_min, self.r_Rx_min, self.λ0, self.intLoss, self.I_Tx_Function0, self.K, self.t_slice, self.path).progressUpdated.connect(self.update_progress_bar)
        #The first figure in the figs list, is the 3D plot.
        try:
            figs = self.simulation.main(self.H1, self.H2, self.α, self.β, self.n, self.d_T, self.d_R, self.r_Tx_min, self.r_Rx_min, self.λ0, self.intLoss, self.I_Tx_Function0, self.K, self.t_slice, self.path)

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
        
        self.display_3D_plot_trace_update(self.fig3D, status_text, status_detail)
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

