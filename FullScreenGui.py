import sys
import os
import xml.etree.ElementTree as ET
from PyQt5.QtCore import QFile, QTextStream, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QLineEdit, QPushButton, QTextEdit, QTabWidget, QFileDialog, QAction, QMessageBox, QScrollArea
import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import csv
import json
from mpl_toolkits.axes_grid1 import make_axes_locatable
import math

AVAGADRO_NUM = 6.023E23
CM_TO_BARN = 1.0E-24 # converts cm^2 to barns
SAMPLING_RATE = 100.0 # Hz
ELEMENTARY_CHARGE = 1.60E-19 # in C
D_OMEGA_= 0.00463 # slit settings in steradians
Z = 1 # Number of protons in beam

def get_next_blank_row(table):
    # Get the total number of rows in the table
    total_rows = table.rowCount()

    # Loop through each row
    for i in range(total_rows):
        # Check if every cell in the row is empty
        row_empty = all(table.item(i, j) is None for j in range(table.columnCount()))

        # If the row is empty, return its index
        if row_empty:
            return int(i)

    # If no empty row is found, return the next row index
    return int(total_rows)

def get_table_data(table):
    data = []
    for i in range(table.rowCount()):
        row = []
        for j in range(table.columnCount()):
            item = table.item(i, j)
            if item is not None:
                if len(item.text()) == 0:
                    row.append(np.nan)
                else:
                    row.append(float(item.text()))
            else:
                row.append(np.nan)
        data.append(row)

    # Convert data to numpy array
    data = np.array(data)
    return data

def cross_section_calculation(BCI_hit, BCI_scale, targetThickness, molarMass, volume, volume_err): #func used to convert mass in ug/cm --> 1/barn

    rho_t = (targetThickness * CM_TO_BARN * AVAGADRO_NUM)/(molarMass)
    Q_beam = (BCI_hit * 1E-9 * BCI_scale)/(SAMPLING_RATE)
    N_beam = Q_beam / ELEMENTARY_CHARGE
    dsigma_domega = (volume * 1000)/(N_beam * rho_t * D_OMEGA_)  # cross-sec in mb/sr

    err_BCI = 0.15 * BCI_hit
    if volume == 0.0:
        deltaX = 0.0
    else:
        deltaX = np.sqrt( (volume_err/volume)**2 + (err_BCI/BCI_hit)**2 ) * dsigma_domega
    
    dsigma_domega = round(dsigma_domega, 7)
    deltaX = round(deltaX, 7)
    
    return dsigma_domega, deltaX

def general_xml(file,name):
    #Wrote by Bryan Kelly to extract the xml format fit file from HDTV to a easily readable table if wanted
    mytree = ET.parse(file)
    myroot = mytree.getroot()
 
    uncal_fit_list = []
    uncal_fit_err_list = []
    uncal_width_list = []
    uncal_width_err_list = []
    uncal_volume_list = []
    uncal_volume_err_list = []

    cal_fit_list = []
    cal_fit_err_list = []
    cal_width_list = []
    cal_width_err_list = []
    cal_volume_list = []
    cal_volume_err_list = []

    for fit in myroot:
        for i in fit:
            if i.tag == 'peak':
                for child in i.iter():
                    if child.tag == 'uncal':
                        for j in child.iter():
                            if j.tag == 'pos':
                                for newchild in j.iter():
                                    if newchild.tag == 'value':
                                        fit_value = newchild.text
                                        uncal_fit_list.append(round(float(fit_value), 4))
                                    elif newchild.tag == 'error':
                                        fit_err = newchild.text
                                        uncal_fit_err_list.append(round(float(fit_err),4))
                            elif j.tag == 'vol':
                                for newchild in j.iter():
                                    if newchild.tag == 'value':
                                        vol_value = newchild.text
                                        uncal_volume_list.append(round(float(vol_value),4))
                                    elif newchild.tag == 'error':
                                        vol_err = newchild.text
                                        uncal_volume_err_list.append(round(float(vol_err),4))
                            elif j.tag == 'width':
                                for newchild in j.iter():
                                    if newchild.tag == 'value':
                                        width_value = newchild.text
                                        uncal_width_list.append(round(float(width_value),4))
                                    elif newchild.tag == 'error':
                                        width_err = newchild.text
                                        uncal_width_err_list.append(round(float(width_err),4))

                    #gets the calibrated data information                
                    if child.tag == 'cal':
                        for j in child.iter():
                            if j.tag == 'pos':
                                for newchild in j.iter():
                                    if newchild.tag == 'value':
                                        fit_value = newchild.text
                                        cal_fit_list.append(round(float(fit_value), 4))
                                    elif newchild.tag == 'error':
                                        fit_err = newchild.text
                                        cal_fit_err_list.append(round(float(fit_err),4))
                            elif j.tag == 'vol':
                                for newchild in j.iter():
                                    if newchild.tag == 'value':
                                        vol_value = newchild.text
                                        cal_volume_list.append(round(float(vol_value),4))
                                    elif newchild.tag == 'error':
                                        vol_err = newchild.text
                                        cal_volume_err_list.append(round(float(vol_err),4))
                            elif j.tag == 'width':
                                for newchild in j.iter():
                                    if newchild.tag == 'value':
                                        width_value = newchild.text
                                        cal_width_list.append(abs(round(float(width_value),4)))
                                    elif newchild.tag == 'error':
                                        width_err = newchild.text
                                        cal_width_err_list.append(round(float(width_err),4))
    
    # calibrated data handling
    cal_energy = []
    cal_energy_err = []
    cal_use = []
    for _ in range(len(cal_fit_list)):
        cal_use.append(np.nan)
        cal_energy.append(np.nan)
        cal_energy_err.append(np.nan)

    #csv file
    fname = name.split('.')[0]
    storefile = f'{fname}.csv'

    uncal_list = list(zip(cal_use, cal_energy, cal_energy_err, uncal_fit_list, uncal_fit_err_list, uncal_width_list, uncal_width_err_list, uncal_volume_list, uncal_volume_err_list))
    uncal_list.sort(key=lambda x:x[3], reverse=True)
    cal_list = list(zip(cal_use, cal_energy, cal_energy_err, cal_fit_list, cal_fit_err_list, cal_width_list, cal_width_err_list, cal_volume_list, cal_volume_err_list))
    cal_list.sort(key=lambda x:x[3])

    cal_flag = True
    if (uncal_fit_list[0] == cal_fit_list[0]):
        cal_flag = False

        with open(storefile, 'w') as f:
            writer = csv.writer(f, delimiter=',')
            for row in uncal_list:
                writer.writerow(row)        
        return storefile, cal_flag
    else:
        with open(storefile, 'w') as f:
            writer = csv.writer(f, delimiter=',')
            for row in cal_list:
                writer.writerow(row)        
        return storefile, cal_flag

def save_data(data, name):
    with open(name + '.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(data)

def load_data(name):
    with open(name, 'r') as csvfile:
        reader = csv.reader(csvfile)
        return [row for row in reader]

def linear_func(x, m, c):
    return m*x + c

def poly2_func(x, a, b, c):
    return a*x*x + b*x + c 

NumAngles = 10
minAngle = 15
maxAngle = 65
stepAngle = 5
CROSS_SEC_INDEX = 11
INPUT_INDEX = 0

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.tables = []

        self.setWindowTitle("SPS Calibration")
        self.setGeometry(100, 100, 1600, 1125)
        # Create save action
        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_to_file)

        # Create load action
        load_action = QAction("Load", self)
        load_action.triggered.connect(self.load_from_file)

        # Add actions to toolbar
        self.toolbar = self.addToolBar("File")
        self.toolbar.addAction(save_action)
        self.toolbar.addAction(load_action)

        def create_input_tab(self, Name):
            table = QTableWidget(self)
            table.setRowCount(10)
            table.setColumnCount(3)
            table.setFixedSize(1100, 500)
            table.setHorizontalHeaderLabels(["Angle (deg)", "BCI Hits", "BCI scale (nA)"])
            table.setColumnWidth(0,358)
            table.setColumnWidth(1,358)
            table.setColumnWidth(2,358)

            # Create input field for name
            self.name_label = QLabel("Name:", self)
            name_input = QLineEdit()
            name_input.setObjectName("Name Input")

            self.target_thickness = QLabel("Target Thickness (\u03BCg/cm\u00B2):", self)
            targetThickness_input = QLineEdit()
            targetThickness_input.setObjectName("Target Thickness (\u03BCg/cm\u00B2):")

            self.molarMass = QLabel("Molar Mass (\u03BCg/mol):", self)
            molarMass_input = QLineEdit()
            molarMass_input.setObjectName("Molar Mass (\u03BCg/mol):")

            self.save_button = QPushButton("Save", self)
            self.save_button.clicked.connect(self.save)

            self.load_button = QPushButton("Load", self)
            self.load_button.clicked.connect(self.load)

            self.load_volume_file_button = QPushButton("Load Volume File", self)
            self.load_volume_file_button.clicked.connect(self.load_vol_file)
            
            text_display = QTextEdit()
            text_display.setReadOnly(True)


            #Create the add/remove buttons
            self.add_row_button = QPushButton("Add Row")
            self.add_row_button.clicked.connect(self.add_row)
            self.remove_row_button = QPushButton("Remove Row")
            self.remove_row_button.clicked.connect(self.remove_row)

            figure = plt.figure(figsize=(10,6))
            canvas = FigureCanvas(figure)
            toolbar = NavigationToolbar(canvas, self)

            # Create layout and add widgets
            
            left_layout = QVBoxLayout()
            right_layout = QVBoxLayout()
            
            h_layout = QHBoxLayout()
            targetThickness_layout = QHBoxLayout()
            molarMass_layout = QHBoxLayout()
            
            left_layout.addWidget(table)
            left_layout.addWidget(self.add_row_button)
            left_layout.addWidget(self.remove_row_button)
            h_layout.addWidget(self.name_label)
            h_layout.addWidget(name_input)

            
            targetThickness_layout.addWidget(self.target_thickness)
            targetThickness_layout.addWidget(targetThickness_input)
            molarMass_layout.addWidget(self.molarMass)
            molarMass_layout.addWidget(molarMass_input)

            left_layout.addLayout(targetThickness_layout)
            left_layout.addLayout(molarMass_layout)
            left_layout.addLayout(h_layout)
            left_layout.addWidget(self.save_button)
            left_layout.addWidget(self.load_button)
            left_layout.addWidget(text_display)
            right_layout.addWidget(self.load_volume_file_button)
            right_layout.addWidget(toolbar)
            right_layout.addWidget(canvas)
            split_layout = QHBoxLayout()
            split_layout.addLayout(left_layout)
            split_layout.addLayout(right_layout)
            split_layout.addStretch(1)

            tab = QWidget()
            tab.setLayout(split_layout)
            tab.table = table
            tab.text_display = text_display
            tab.name_input = name_input
            tab.targetThickness_input = targetThickness_input
            tab.molarMass_input = molarMass_input

            self.tables.append(table)

            return tab

        
        def create_tab(self,Name):

            # Create table for data input
            table = QTableWidget(self)
            table.setRowCount(3)
            table.setColumnCount(9)
            table.setFixedSize(1100, 600)
            table.setHorizontalHeaderLabels(["1 = Use", "Energy [keV]", "Uncertainty [keV]", "Position", "Uncertainty", "Width", "Uncertainty", "Volume", "Uncertainty"])
            table.setColumnWidth(0,75)
            table.setColumnWidth(1,125)
            table.setColumnWidth(2,125)
            table.setColumnWidth(3,125)
            table.setColumnWidth(4,125)
            table.setColumnWidth(5,125)
            table.setColumnWidth(6,125)
            table.setColumnWidth(7,125)
            table.setColumnWidth(8,125)


            # Create input field for name
            self.name_label = QLabel("Name:", self)
            name_input = QLineEdit()
            name_input.setObjectName("Name Input")

            # Create "Run" button
            self.run_button = QPushButton("Run", self)
            self.run_button.clicked.connect(self.run)

            self.save_button = QPushButton("Save", self)
            self.save_button.clicked.connect(self.save)

            self.load_button = QPushButton("Load", self)
            self.load_button.clicked.connect(self.load)
            
            text_display = QTextEdit()
            text_display.setReadOnly(True)
    

            #Create the add/remove buttons
            self.add_row_button = QPushButton("Add Row")
            self.add_row_button.clicked.connect(self.add_row)
            self.remove_row_button = QPushButton("Remove Row")
            self.remove_row_button.clicked.connect(self.remove_row)
            
            figure = plt.figure(figsize=(10,6))
            canvas = FigureCanvas(figure)
            toolbar = NavigationToolbar(canvas, self)
            
            # Create layout and add widgets
            
            left_layout = QVBoxLayout()
            right_layout = QVBoxLayout()
            
            h_layout = QHBoxLayout()
            
            left_layout.addWidget(table)
            left_layout.addWidget(self.add_row_button)
            left_layout.addWidget(self.remove_row_button)
            h_layout.addWidget(self.name_label)
            h_layout.addWidget(name_input)
            left_layout.addLayout(h_layout)
            left_layout.addWidget(self.save_button)
            left_layout.addWidget(self.load_button)
            left_layout.addWidget(text_display)
            right_layout.addWidget(self.run_button)
            right_layout.addWidget(toolbar)
            right_layout.addWidget(canvas)
            split_layout = QHBoxLayout()
            split_layout.addLayout(left_layout)
            split_layout.addLayout(right_layout)
            split_layout.addStretch(1)

            tab = QWidget()
            tab.setLayout(split_layout)
            tab.table = table
            tab.canvas = canvas
            tab.figure = figure
            tab.text_display = text_display
            tab.name_input = name_input
            tab.toolbar = toolbar

            self.tables.append(table)

            return tab

        def create_cross_section_tab(self, Name):
            # Create table for data input
            table = QTableWidget(self)
            table.setRowCount(3)
            table.setColumnCount(22)
            table.setFixedSize(1100, 600)
            table.setHorizontalHeaderLabels(["1 = Use", "Energy [keV]", "15-deg", "Uncert", "20-deg", "Uncert", "25-deg", "Uncert", "30-deg", "Uncert", "35-deg", "Uncert",\
                                                "40-deg", "Uncert", "45-deg", "Uncert", "50-deg", "Uncert", "55-deg", "Uncert", "60-deg", "Uncert"])
          
            for i in range(23):
                if i == 0:
                    table.setColumnWidth(i, 50)
                else:
                    table.setColumnWidth(i, 100)
            # Create input field for name
            self.name_label = QLabel("Name:", self)
            name_input = QLineEdit()
            name_input.setObjectName("Name Input")

            # Create "Run" button
            self.run_button = QPushButton("Run", self)
            self.run_button.clicked.connect(self.run)

            self.save_button = QPushButton("Save", self)
            self.save_button.clicked.connect(self.save)

            self.load_button = QPushButton("Load", self)
            self.load_button.clicked.connect(self.load)

            self.plot_button = QPushButton("Plot Cross-Section", self)
            self.plot_button.clicked.connect(self.plot)

            self.plot_button_wEnergy = QPushButton("Plot Cross-Section w/ Energy Residuals", self)
            self.plot_button_wEnergy.clicked.connect(self.plot_wEnergyResiduals)

            self.save_x_sec_button = QPushButton("Save Cross-Section", self)
            self.save_x_sec_button.clicked.connect(self.save_cross_section)

            self.save_x_sec_plot_button = QPushButton("Save Angular Distribution Plot", self)
            self.save_x_sec_plot_button.clicked.connect(self.save_cross_section_plot)

            self.clear_plot_button = QPushButton("Clear Plots", self)
            self.clear_plot_button.clicked.connect(self.clear_plots)
            
            text_display = QTextEdit()
            text_display.setReadOnly(True)
    

            #Create the add/remove buttons
            self.add_row_button = QPushButton("Add Row")
            self.add_row_button.clicked.connect(self.add_row)
            self.remove_row_button = QPushButton("Remove Row")
            self.remove_row_button.clicked.connect(self.remove_row)
            
            figure = plt.figure(figsize=(12,8))
            canvas = FigureCanvas(figure)
            toolbar = NavigationToolbar(canvas, self)
            
            # Create layout and add widgets
            
            left_layout = QVBoxLayout()
            right_layout = QVBoxLayout()
            
            h_layout = QHBoxLayout()
            
            left_layout.addWidget(table)
            left_layout.addWidget(self.add_row_button)
            left_layout.addWidget(self.remove_row_button)
            h_layout.addWidget(self.name_label)
            h_layout.addWidget(name_input)
            left_layout.addLayout(h_layout)
            left_layout.addWidget(self.save_button)
            left_layout.addWidget(self.load_button)
            left_layout.addWidget(text_display)
            right_layout.addWidget(self.run_button)
            right_layout.addWidget(self.plot_button)
            right_layout.addWidget(self.plot_button_wEnergy)
            right_layout.addWidget(self.save_x_sec_button)
            right_layout.addWidget(self.save_x_sec_plot_button)
            right_layout.addWidget(self.clear_plot_button)
            right_layout.addWidget(toolbar)
            #right_layout.addWidget(canvas)

            scroll_area = QScrollArea()
            #canvas.setMaximumWidth(660)
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
            scroll_area.setWidgetResizable(True)
            scroll_area.setWidget(canvas)
            right_layout.addWidget(scroll_area)

            split_layout = QHBoxLayout()
            split_layout.addLayout(left_layout)
            split_layout.addLayout(right_layout)

            tab = QWidget()
            tab.setLayout(split_layout)
            tab.table = table
            tab.canvas = canvas
            tab.figure = figure
            tab.text_display = text_display
            tab.name_input = name_input
            tab.toolbar = toolbar
            tab.scroll_area = scroll_area

            return tab

        tabwidget = QTabWidget()

        self.input_tab = create_input_tab(self, "Input")
        tabwidget.addTab(self.input_tab, "Input")

        self.tab15 = create_tab(self, "15-deg")
        tabwidget.addTab(self.tab15, "15-deg")

        self.tab20 = create_tab(self, "20-deg")
        tabwidget.addTab(self.tab20, "20-deg")

        self.tab25 = create_tab(self, "25-deg")
        tabwidget.addTab(self.tab25, "25-deg")

        self.tab30 = create_tab(self, "30-deg")
        tabwidget.addTab(self.tab30, "30-deg")

        self.tab35 = create_tab(self, "35-deg")
        tabwidget.addTab(self.tab35, "35-deg")

        self.tab40 = create_tab(self, "40-deg")
        tabwidget.addTab(self.tab40, "40-deg")

        self.tab45 = create_tab(self, "45-deg")
        tabwidget.addTab(self.tab45, "45-deg")

        self.tab50 = create_tab(self, "50-deg")
        tabwidget.addTab(self.tab50, "50-deg")

        self.tab55 = create_tab(self, "55-deg")
        tabwidget.addTab(self.tab55, "55-deg")

        self.tab60 = create_tab(self, "60-deg")
        tabwidget.addTab(self.tab60, "60-deg")

        self.tab_crossSec = create_cross_section_tab(self, "Cross Sections")
        tabwidget.addTab(self.tab_crossSec, "Cross Sections")

        central_layout = QVBoxLayout()
        central_layout.addWidget(tabwidget)


        central_widget = QWidget(self)
        central_widget.setLayout(central_layout)
        self.setCentralWidget(central_widget)
        self.tabwidget = tabwidget


    def add_row(self):
        current_tab_index = self.tabwidget.currentIndex()
        current_tab = self.tabwidget.widget(current_tab_index)

        table = current_tab.table
        row_count = table.rowCount()
        table.insertRow(row_count)

    def remove_row(self):

        current_tab_index = self.tabwidget.currentIndex()
        current_tab = self.tabwidget.widget(current_tab_index)
        table = current_tab.table

        selected_rows = table.selectedIndexes()
        if selected_rows:
            row = selected_rows[0].row()
            table.removeRow(row)
    
    def load_vol_file(self):
        current_tab_index = self.tabwidget.currentIndex()
        current_tab = self.tabwidget.widget(current_tab_index)
        current_table = current_tab.table
        # canvas = current_tab.canvas
        # figure = current_tab.figure
        text_display = current_tab.text_display
        name_input = current_tab.name_input
        text_display.clear()

        # Get name from input field
        name = name_input.text()

        data = []
        with open(name, 'r') as f:
            stripped = [s.strip() for s in f]
            for line in stripped:
                data.append(line.split('\t'))
        energy = name.split('_')[0]
        i=0
        for tab_index in range(1, self.tabwidget.count() - 1):
            tab = self.tabwidget.widget(tab_index)
            current_table = tab.findChild(QTableWidget)
            row = get_next_blank_row(current_table)
            current_table.setItem(row,1, QTableWidgetItem(energy))
            current_table.setItem(row,7, QTableWidgetItem(str(data[i][0])))
            current_table.setItem(row,8, QTableWidgetItem(str(data[i][1])))
            i+=1

        text_display.setPlainText(f"File {name} loaded successfully")

    
    def save_cross_section(self):
        current_tab_index = self.tabwidget.currentIndex()
        current_tab = self.tabwidget.widget(current_tab_index)
        current_table = current_tab.table
        text_display = current_tab.text_display

        data = get_table_data(current_table)
        break_flag = False
        counter = 0
        file_list = []
        for i, row in enumerate(data):
            if data[i][0] == 1:
                x_sec = []
                err = []
                for j, value in enumerate(row):
                    if j == 0:
                        continue
                    elif j == 1:
                        if np.isnan(value):
                            text_display.setPlainText(f"Energy of state needed from row {i+1} to save angular distribution")
                            break_flag = True
                            break
                        else:
                            energy = value
                    else:
                        if j % 2 == 0:  
                            x_sec.append(value)
                        elif j % 2 != 0:
                            err.append(value)
                if break_flag:
                    break
                fname_energy = int(energy)
                storefile = f"{fname_energy}_keV.txt"
                file_list.append(storefile)
                with open(storefile, 'w') as f:
                    writer = csv.writer(f, delimiter='\t')
                    writer.writerows(zip(x_sec, err))
                counter+=1
        text_display.append(f"Successfully written {counter} file(s):")
        for file in file_list:
            text_display.append(f"{file}")
        
    def save_cross_section_plot(self):
        current_tab_index = self.tabwidget.currentIndex()
        current_tab = self.tabwidget.widget(current_tab_index)
        current_table = current_tab.table
        text_display = current_tab.text_display
        canvas = current_tab.canvas
        figure = current_tab.figure

        subplots = canvas.figure.get_axes()
        
        break_flag = False
        for ax in subplots:
            extent = ax.get_tightbbox(figure.canvas.renderer).transformed(figure.dpi_scale_trans.inverted())
            if np.isnan(float(ax.get_title().split(' ')[0])):
                text_display.setPlainText("No energy listed for excited state in at least one of angular distributions, enter energy and re-save plot.")
                break_flag = True
                break
            else:
                temp = float(ax.get_title().split(' ')[0])
                energy = int(temp)
                savestring = f"{energy}_keV_angulardist.png"
                figure.savefig(savestring, bbox_inches=extent.expanded(1.1, 1.2))

        if not break_flag:
            text_display.setPlainText("Successfully saved angular distributions!")


    def run(self):
        current_tab_index = self.tabwidget.currentIndex()
        current_tab = self.tabwidget.widget(current_tab_index)
        current_table = current_tab.table
        canvas = current_tab.canvas
        figure = current_tab.figure
        text_display = current_tab.text_display
        name_input = current_tab.name_input


        # Get name from input field
        name = name_input.text()
        text_display.clear()

        if current_tab_index != CROSS_SEC_INDEX and current_tab_index != INPUT_INDEX:
            # Get data from table
            data = get_table_data(current_table)
            figure.clear()
            
            
            ##########################################################################################################################################
            length = len(data)

            pos = np.array([])
            pos_err = np.array([])
            energy = np.array([])
            energy_err = np.array([])
            width = np.array([])
            width_err = np.array([])
            vol = np.array([])
            vol_err = np.array([])

            for i in range(length):
                if data[i][0] == 1:
                    energy = np.append(energy,data[i][1])
                    energy_err = np.append(energy_err,data[i][2])
                    pos = np.append(pos,data[i][3])
                    pos_err = np.append(pos_err,data[i][4])
                    width = np.append(width,data[i][5])
                    width_err = np.append(width_err,data[i][6])
                    vol = np.append(vol, data[i][7])
                    vol_err = np.append(vol_err, data[i][8])


            k=1
            def weight_func(x,y,x_err,y_err):
                return np.sqrt((x_err*k)**2+(y_err)**2)
            
            # Angle Tabs 
            # Fit the data using curve_fit
            popt_linear, pcov_linear = curve_fit(linear_func, pos, energy, sigma=weight_func(pos,energy,pos_err,energy_err), absolute_sigma=True)
            slope, intercept = popt_linear
            
            popt_poly2, pcov_poly2 = curve_fit(poly2_func, pos, energy, sigma=weight_func(pos,energy,pos_err,energy_err), absolute_sigma=True)
            a_2, b_2, c_2 = popt_poly2

            text_display.setPlainText(f"Linear: [0, {slope}, {intercept}]\nPolynomial: [{a_2}, {b_2}, {c_2}]")

            # Get the energy calibrated
            energy_calibrated_linear = linear_func(pos,slope,intercept)
            energy_calibrated_poly2 = poly2_func(pos,a_2,b_2,c_2)
            
            #0-7 MeV Range
            pos_range = np.linspace(-200,125,600)
            Total_energy_calibrated_linear = linear_func(pos_range,slope,intercept)
            Total_energy_calibrated_poly2 = poly2_func(pos_range,a_2,b_2,c_2)

            # Get the residuals
            residuals_linear = energy - energy_calibrated_linear
            residuals_poly2 = energy - energy_calibrated_poly2

            # Plot energy vs position
            ax1 = figure.add_subplot(211)        
            ax1.errorbar(pos, energy, xerr=pos_err, yerr=energy_err, fmt='ko', label='Data')
            ax1.plot(pos_range, Total_energy_calibrated_linear,'r', label='Linear')
            ax1.plot(pos_range, Total_energy_calibrated_poly2,'b', label='2nd Order Polynomial')
            ax1.set_xlabel('Position [Channel]')
            ax1.set_ylabel('Energy [keV]')
            ax1.set_title(f"{name}")
            ax1.legend()

            # Plot residuals
            ax2 = figure.add_subplot(212)        
            ax2.plot(energy, np.zeros(len(energy)),'k')
            ax2.errorbar(energy, residuals_linear, yerr=weight_func(pos,energy,pos_err,energy_err), fmt='ro', label='Linear', capsize=4)
            ax2.errorbar(energy, residuals_poly2, yerr=weight_func(pos,energy,pos_err,energy_err), fmt='bo', label='2nd Order Polynomial', capsize=4)
            ax2.set_xlabel('Energy [keV]')
            ax2.set_ylabel('Residuals')
            ax2.legend()

            figure.subplots_adjust(top=0.95, bottom=0.05)

            figure.savefig(f"{name}")

        elif current_tab_index == CROSS_SEC_INDEX:
            # Cross section tab

            max_rows = 0
            for tab in range(1,self.tabwidget.count() - 1):
                table = self.tabwidget.widget(tab).findChild(QTableWidget)
                if table.rowCount() > max_rows:
                    max_rows = table.rowCount()
            matched_rows = []
            energy_list = []
            count = 0 # counter that sets the row in the cross-section table
            for i in range(max_rows):
                if self.tabwidget.widget(1).findChild(QTableWidget).item(i, 1) is not None:
                    energy = self.tabwidget.widget(1).findChild(QTableWidget).item(i, 1).text()
                    energy_list.append(energy)
                    matching_rows = []
                    for tab in range(1, self.tabwidget.count() - 1):
                        table = self.tabwidget.widget(tab).findChild(QTableWidget)
                        for row in range(table.rowCount()):
                            if table.item(row, 1) is not None:
                                if table.item(row, 1).text() == energy:
                                    matching_rows.append(row)
                    if len(matching_rows) == self.tabwidget.count() - 2:
                        matched_rows.append((count, matching_rows))
                        count +=1
                else:
                    continue

            current_table.setRowCount(len(matched_rows))
            targetThickness = float(self.tabwidget.widget(0).targetThickness_input.text())
            molarMass = float(self.tabwidget.widget(0).molarMass_input.text())

            temp = []
            for i in energy_list:  # flush out any 'nans' that made it into the energy list
                if np.isnan(float(i)):
                    continue
                else:
                    temp.append(i)
            energy_list = temp

            for i, matching_rows in matched_rows:
                k = 2
                l = 0
                current_table.setItem(i,1, QTableWidgetItem(energy_list[i]))
                for tab, row in enumerate(matching_rows):
                    BCI_hit = float(self.tabwidget.widget(0).findChild(QTableWidget).item(l, 1).text())
                    BCI_scale = float(self.tabwidget.widget(0).findChild(QTableWidget).item(l, 2).text())
                    table = self.tabwidget.widget(tab + 1).findChild(QTableWidget)
                    val = table.item(row, 7)
                    err = table.item(row, 8)
                    if val is not None:
                        volume = float(val.text())
                        err = float(err.text())
                        x_sec, error = cross_section_calculation(BCI_hit, BCI_scale, targetThickness, molarMass, volume, err)
                        current_table.setItem(i,k, QTableWidgetItem(str(x_sec)))
                        current_table.setItem(i,k + 1, QTableWidgetItem(str(error)))
                    else:
                        current_table.setItem(i,k, QTableWidgetItem(str(0.0)))
                        current_table.setItem(i,k + 1, QTableWidgetItem(str(0.0)))
                    k+=2
                    l+=1
            text_display.setPlainText("All possible cross-sections calculated!")

        canvas.draw()
    def clear_plots(self):
        current_tab_index = self.tabwidget.currentIndex()
        current_tab = self.tabwidget.widget(current_tab_index)
        current_table = current_tab.table
        canvas = current_tab.canvas
        figure = current_tab.figure
        axes = figure.get_axes()
        print(len(axes))
        for ax in axes:
            figure.delaxes(ax)
        # figure.delaxes(axes)
        figure.clear()
        newaxes = figure.get_axes()
        print(len(newaxes))
        canvas.axes.cla()

        
    def plot_wEnergyResiduals(self):
        current_tab_index = self.tabwidget.currentIndex()
        current_tab = self.tabwidget.widget(current_tab_index)
        current_table = current_tab.table
        canvas = current_tab.canvas
        figure = current_tab.figure
        text_display = current_tab.text_display
        name_input = current_tab.name_input


        # Get name from input field
        name = name_input.text()
        text_display.clear()
        figure.clear()

        data = get_table_data(current_table)
        angles = [15,20,25,30,35,40,45,50,55,60]
        cross_sections_list = []
        error_list = []
        excited_state_list = []
        for i, row in enumerate(data):
            if data[i][0] == 1:
                x_sec = []
                err = []
                for j, value in enumerate(row):
                    if j == 0:
                        continue
                    elif j == 1:
                        excited_state_list.append(value)
                    else:
                        if j % 2 == 0:
                            x_sec.append(value)
                        elif j % 2 != 0:
                            err.append(value)
                cross_sections_list.append(x_sec)
                error_list.append(err)
        print(excited_state_list)
        exp_energies = []
        exp_energies_err = []
        for excited_state in excited_state_list:
            temp_energy = []
            temp_err = []
            for tab in range(1,self.tabwidget.count() - 1):
                table = self.tabwidget.widget(tab).findChild(QTableWidget)
                data = get_table_data(table)
                for i, row in enumerate(data):
                    if data[i][1] == excited_state:
                        for j, value in enumerate(row):
                            if j == 3:
                                temp_energy.append(value)
                            if j == 4:
                                temp_err.append(value)
            exp_energies.append(temp_energy)
            exp_energies_err.append(temp_err)
        
        plot_count = len(cross_sections_list)
        plot_space = f'{len(cross_sections_list)}11'
        plot_num = int(plot_space)
        subplot_height = 3  # Set the height of a single subplot in inches
        spacing = 1  # Set spacing between subplots in inches
        total_height = (subplot_height + spacing) * plot_count - spacing  # Calculate the total required height 
        figure.set_size_inches(30, subplot_height)  # Update the figure height
        canvas.setMinimumHeight(total_height * canvas.physicalDpiY())  # Update the canvas height
        miny=0.01
        maxy=1
        for i in range(len(excited_state_list)):
            ax = figure.add_subplot(plot_num)
            divider = make_axes_locatable(ax)
            ax2 = divider.append_axes("bottom", size="20%", pad=0)
            ax.figure.add_axes(ax2)
            figure.add_axes(ax)

            ax.errorbar(angles, cross_sections_list[i], yerr=error_list[i], color='black', fmt='x', ecolor='red', capsize=2.0, label='Data')
            ax.set_xlabel(r'Lab Angle [$\Theta_{lab}$]')
            ax.set_ylabel(r'Cross-Section [$\frac{mb}{sr}$]')
            ax.set_title(f"{excited_state_list[i]} keV")
            ax.set_yscale("log")
            ax.legend()

            ax2.errorbar(angles, exp_energies[i], exp_energies_err[i], color='green', fmt='^', ecolor='#CEB888', markersize=4, capsize=2.0)
            ax2.hlines(excited_state_list[i], 15,60,colors='b', label='NNDC Energy')
            ax2.grid(True)
            ax.set_xticks([])
            ax.minorticks_on()
            ax.set_title(f"{excited_state_list[i]} keV")
            plot_num+=1
            for val in cross_sections_list[i]:
                if val < miny:
                    miny = 0.001
                if val > maxy:
                    maxy = 10
            ax.set_ylim(miny, maxy)
        canvas.draw()
        

    def plot(self):
        """
        Plotting function to be used in the cross-sections tab to display angular distributions
        """
        current_tab_index = self.tabwidget.currentIndex()
        current_tab = self.tabwidget.widget(current_tab_index)
        current_table = current_tab.table
        canvas = current_tab.canvas
        figure = current_tab.figure
        text_display = current_tab.text_display
        name_input = current_tab.name_input
        text_display.clear()
        scroll_area = current_tab.scroll_area

        # Get name from input field
        name = name_input.text()

        # Get data from table
        data = get_table_data(current_table)

        figure.clear()
        canvas.draw()

        angles = [15,20,25,30,35,40,45,50,55,60]
        cross_sections_list = []
        error_list = []
        excited_state_list = []
        for i, row in enumerate(data):
            print(data[i][0], type(data[i][0]))
            if data[i][0] == 1:
                x_sec = []
                err = []
                for j, value in enumerate(row):
                    if j == 0:
                        continue
                    elif j == 1:
                        excited_state_list.append(value)
                    else:
                        if j % 2 == 0:
                            x_sec.append(value)
                        elif j % 2 != 0:
                            err.append(value)
                cross_sections_list.append(x_sec)
                error_list.append(err)
        miny=0.01
        maxy=1
        
        print("# of plots:",len(cross_sections_list))
        if len(cross_sections_list) == 0:
            text_display.setPlainText("No rows selected to generate a cross-section, insert a 1 into the 'Use' tab to select a row!")
        elif len(cross_sections_list) == 1:
            ax = figure.add_subplot(111)
            ax.errorbar(angles, cross_sections_list[0], yerr=error_list[0], color='black', fmt='x', ecolor='red', capsize=2.0, label='Data')
            ax.set_xlabel(r'Lab Angle [$\Theta_{lab}$]')
            ax.set_ylabel(r'Cross-Section [$\frac{mb}{sr}$]')
            ax.set_title(f"{excited_state_list[0]} keV")
            ax.set_yscale("log")
            ax.legend()
            for val in cross_sections_list[0]:
                if val < miny:
                    miny = 0.001
                if val > maxy:
                    maxy = 10
            ax.set_ylim(miny, maxy)
            scroll_area.setWidgetResizable(True)
            scroll_area.setWidget(canvas)
        elif len(cross_sections_list) == 2:
            figure.set_size_inches(8, 6)
            figure.subplots_adjust(hspace=0.375, left=0.125, right = 0.900, top=0.920, bottom=0.080)
            ax = figure.add_subplot(211)
            ax.errorbar(angles, cross_sections_list[0], yerr=error_list[0], color='black', fmt='x', ecolor='red', capsize=2.0, label='Data')
            ax.set_xlabel(r'Lab Angle [$\Theta_{lab}$]')
            ax.set_ylabel(r'Cross-Section [$\frac{mb}{sr}$]')
            ax.set_title(f"{excited_state_list[0]} keV")
            ax.set_yscale("log")
            ax.legend()
            for val in cross_sections_list[0]:
                if val < miny:
                    miny = 0.001
                if val > maxy:
                    maxy = 10
            ax.set_ylim(miny, maxy)
            ax1 = figure.add_subplot(212)
            ax1.errorbar(angles, cross_sections_list[1], yerr=error_list[1], color='black', fmt='x', ecolor='red', capsize=2.0, label='Data')
            ax1.set_xlabel(r'Lab Angle [$\Theta_{lab}$]')
            ax1.set_ylabel(r'Cross-Section [$\frac{mb}{sr}$]')
            ax1.set_title(f"{excited_state_list[1]} keV")
            ax1.set_yscale("log")
            ax1.legend()
            for val in cross_sections_list[1]:
                if val < miny:
                    miny = 0.001
                if val > maxy:
                    maxy = 10
            ax1.set_ylim(miny, maxy)
            scroll_area.setWidgetResizable(True)
            scroll_area.setWidget(canvas)
        else:
            if len(cross_sections_list) > 9:
                text_display.setPlainText("Ploting supports only up to 9 subplots at most! Please try again with less than 10 total subplots!")
            else:
                plot_count = len(cross_sections_list)
                plot_space = f'{len(cross_sections_list)}11'
                plot_num = int(plot_space)
                subplot_height = 4 # Set the height of a single subplot in inches
                spacing = 4 + 0.25 * plot_count  # Set spacing between subplots in inches
                total_height = total_height = subplot_height * plot_count + spacing  #(plot_count - 1)  # Calculate the total required height 
                figure.set_size_inches(6, 4)  # Update the figure height
                print("# of plots to draw:", len(cross_sections_list))
                for i in range(len(cross_sections_list)):
                    ax = figure.add_subplot(plot_num)
                    ax.errorbar(angles, cross_sections_list[i], yerr=error_list[i], color='black', fmt='x', ecolor='red', capsize=2.0, label='Data')
                    ax.set_xlabel(r'Lab Angle [$\Theta_{lab}$]')
                    ax.set_ylabel(r'Cross-Section [$\frac{mb}{sr}$]')
                    ax.set_title(f"{excited_state_list[i]} keV")
                    ax.set_yscale("log")
                    ax.legend()
                    for val in cross_sections_list[i]:
                        if val < miny:
                            miny = 0.001
                        if val > maxy:
                            maxy = 10
                    ax.set_ylim(miny, maxy)
                    plot_num += 1
                # figure.subplots_adjust(hspace=1.036/plot_count, top=3.912/plot_count, bottom=0.152/plot_count, left=0.456/plot_count, right=3.92/plot_count, wspace=1.1/plot_count)
                figure.subplots_adjust(hspace=0.25, left=0.196/plot_count, right =(1.39106594*plot_count**-0.84379591), top=0.985, bottom=0.035)
                canvas.setMinimumSize(int(total_height * canvas.physicalDpiY()), int(total_height * canvas.physicalDpiY()))
                canvas.setMaximumSize(int(total_height * canvas.physicalDpiY()), int(total_height * canvas.physicalDpiY()))
                scroll_area.setWidgetResizable(True)
                scroll_area.setWidget(canvas)
        canvas.draw()

    def save(self):
        current_tab_index = self.tabwidget.currentIndex()
        current_tab = self.tabwidget.widget(current_tab_index)
        table = current_tab.table
        name_input = current_tab.name_input


        name = name_input.text()
        data = []
        for i in range(table.rowCount()):
            row = []
            for j in range(table.columnCount()):
                item = table.item(i, j)
                if item is not None:
                    row.append(float(item.text()))
                else:
                    row.append(np.nan)
            data.append(row)
        save_data(data, name)

    def load(self):

        current_tab_index = self.tabwidget.currentIndex()
        current_tab = self.tabwidget.widget(current_tab_index)
        table = current_tab.table
        name_input = current_tab.name_input
        text_display = current_tab.text_display

        name = name_input.text()

        if current_tab_index == INPUT_INDEX:
            molarMass_input = current_tab.molarMass_input
            targetThickness_input = current_tab.targetThickness_input
            if (name.endswith("input.txt")):
                BCI_data = []
                targetinfo = []
                i=0
                with open(name, 'r') as f:
                    stripped = [s.strip() for s in f]
                    for line in stripped:
                        if line.startswith('#'):
                            continue
                        if i == 0:
                            targetinfo.append(line.split('\t'))
                        else:
                            BCI_data.append(line.split('\t'))
                        i+=1

                table.setRowCount(0)
                table.setRowCount(len(BCI_data))
                molarMass_input.setText(str(targetinfo[0][0]))
                targetThickness_input.setText(str(targetinfo[0][1]))

                for i, row in enumerate(BCI_data):
                    for j, value in enumerate(row):
                        item = QTableWidgetItem(str(value))
                        table.setItem(i,j,item)
                text_display.setPlainText('Input file loaded sucessfully!')

            else:
                text_display.setPlainText(f'Failed to load file: {name}')
        
        else:
            file_extension = os.path.splitext(name)[1]
            if file_extension == '.xml':
                csvfile, cal_flag = general_xml(name,name)
            elif file_extension == '.fit':
                csvfile, cal_flag = general_xml(name,name)

            if cal_flag:
                text_display.setPlainText("Calibrated data set, position & uncertainty in [keV]")
            else:
                text_display.setPlainText("Uncalibrated data set, position & uncertainty in [channel]")
            data = load_data(csvfile)
            os.remove(csvfile)

            # Clear the table before loading new data
            table.setRowCount(0)
            table.setRowCount(len(data))

            for i, row in enumerate(data):
                for j, value in enumerate(row):
                    item = QTableWidgetItem(str(value))
                    table.setItem(i, j, item)
    
    def save_to_file(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        file_name, _ = QFileDialog.getSaveFileName(self, "Save File", "", "JSON Files (*.json);;All Files (*)", options=options)
        if file_name:
            data = {}
            for tab_index in range(self.tabwidget.count()):
                tab = self.tabwidget.widget(tab_index)
                table = tab.findChild(QTableWidget)
                if table:
                    table_data = []
                    for row in range(table.rowCount()):
                        row_data = []
                        for col in range(table.columnCount()):
                            item = table.item(row, col)
                            if item:
                                row_data.append(item.text())
                            else:
                                row_data.append('')
                        table_data.append(row_data)
                    data[f"tab{tab_index}"] = table_data

                # Add any QLineEdit objects to the dictionary
                line_edit_data = {}
                for line_edit in tab.findChildren(QLineEdit):
                    line_edit_name = line_edit.objectName()
                    line_edit_text = line_edit.text()
                    line_edit_data[line_edit_name] = line_edit_text
                if line_edit_data:
                    data[f"lineedits_{tab_index}"] = line_edit_data

            file = QFile(file_name)
            if file.open(QFile.WriteOnly | QFile.Text):
                stream = QTextStream(file)
                stream << json.dumps(data)
                file.close()

    def load_from_file(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        file_name, _ = QFileDialog.getOpenFileName(self, "Open File", "", "JSON Files (*.json);;All Files (*)", options=options)
        if file_name:
            file = QFile(file_name)
            if file.open(QFile.ReadOnly | QFile.Text):
                stream = QTextStream(file)
                data = json.loads(stream.readAll())
                file.close()
                j=0
                for tab_index, table_data in data.items(): 
                    if (tab_index.startswith("tab")):
                        tab_index = int(tab_index[3:])
                        tab = self.tabwidget.widget(tab_index)

                        # Load the data for any QTableWidget
                        table = tab.findChild(QTableWidget)
                        if table:
                            num_rows = len(table_data)
                            num_cols = len(table_data[0])
                            table.setRowCount(num_rows)
                            table.setColumnCount(num_cols)
                            for row_index, row_data in enumerate(table_data):
                                for col_index, item_data in enumerate(row_data):
                                    if item_data == '':
                                        table.setItem(row_index, col_index, None)
                                    else:
                                        item = QTableWidgetItem(item_data)
                                        table.setItem(row_index, col_index, item)

                    # Load the data for any QLineEdit objects
                    elif (tab_index.startswith("lineedits_")):
                        tab_index = int(tab_index[10:])
                        tab = self.tabwidget.widget(tab_index)
                        line_edit_data = data.get(f"lineedits_{tab_index}")
                        if line_edit_data:
                            for line_edit_name, line_edit_text in line_edit_data.items():
                                line_edit = tab.findChild(QLineEdit, line_edit_name)
                                if line_edit:
                                    line_edit.setText(line_edit_text)

        
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())




# GAMMA DETECTOR CALIBRATION
        # # Fit the data using curve_fit
        # popt_linear, pcov_linear = curve_fit(linear_func, pos, energy, sigma=weight_func(pos,energy,pos_err,energy_err), absolute_sigma=True)
        # slope, intercept = popt_linear
        
        # popt_poly2, pcov_poly2 = curve_fit(poly2_func, pos, energy, sigma=weight_func(pos,energy,pos_err,energy_err), absolute_sigma=True)
        
        # a_2, b_2, c_2 = popt_poly2

        # popt_linear_width, pcov_linear_width = curve_fit(linear_func, energy, width, sigma=weight_func(energy,width,energy_err,width_err), absolute_sigma=True)
        # slope_width, intercept_width = popt_linear_width

        # text_display.setPlainText(f"Linear: [0, {slope}, {intercept}]\nPolynomial: [{a_2}, {b_2}, {c_2}]\
        # \n\n~Width [Channels]:\n\
        # \t  500 keV =  {round(500*slope_width+intercept_width)}\n\
        # \t1000 keV = {round(1000*slope_width+intercept_width)}\n\
        # \t1500 keV = {round(1500*slope_width+intercept_width)}\n\
        # \t2000 keV = {round(2000*slope_width+intercept_width)}\n\
        # \t2500 keV = {round(2500*slope_width+intercept_width)}\n")

        # # Get the energy calibrated
        # energy_calibrated_linear = linear_func(pos,slope,intercept)
        # energy_calibrated_poly2 = poly2_func(pos,a_2,b_2,c_2)
        
        # #0-7 MeV Range
        # pos_range = np.linspace(0,4096,2048)
        # Total_energy_calibrated_linear = linear_func(pos_range,slope,intercept)
        # Total_energy_calibrated_poly2 = poly2_func(pos_range,a_2,b_2,c_2)

        # width_range = np.linspace(0,3300,3300)
        # fit_width = linear_func(width_range,slope_width,intercept_width)

        # # Get the residuals
        # residuals_linear = energy - energy_calibrated_linear
        # residuals_poly2 = energy - energy_calibrated_poly2

        # # Plot energy vs position
        # ax1 = figure.add_subplot(311)        
        # ax1.errorbar(pos, energy, xerr=pos_err, yerr=energy_err, fmt='ko', label='Data')
        # ax1.plot(pos_range, Total_energy_calibrated_linear,'r', label='Linear')
        # ax1.plot(pos_range, Total_energy_calibrated_poly2,'b', label='2nd Order Polynomial')
        # ax1.set_xlabel('Position [Channel]')
        # ax1.set_ylabel('Energy [keV]')
        # ax1.set_title(f"{name}")
        # ax1.legend()

        # # Plot residuals
        # ax2 = figure.add_subplot(312)        
        # ax2.plot(energy, np.zeros(len(energy)),'k')
        # # ax2.errorbar(energy, residuals_linear, yerr=weight_func(pos,energy,pos_err,energy_err), fmt='ro', label='Linear', capsize=4)
        # ax2.errorbar(energy, residuals_poly2, yerr=weight_func(pos,energy,pos_err,energy_err), fmt='bo', label='2nd Order Polynomial', capsize=4)
        # ax2.set_xlabel('Energy [keV]')
        # ax2.set_ylabel('Residuals')
        # ax2.legend()

        # #Width in channel
        # ax3 = figure.add_subplot(313)        
        # ax3.plot(width_range,fit_width,'k')
        # ax3.errorbar(energy, width, yerr=weight_func(width,energy,width_err,energy_err), fmt='bo', capsize=4)
        # ax3.set_xlabel('Energy [keV]')
        # ax3.set_ylabel('Width [Channel]')

        # figure.subplots_adjust(top=0.95, bottom=0.05)

        # figure.savefig(f"{name}")

# PREVIOUSLY WORKING GOOD CODE for run function on cross-sec tab
    # max_rows = 0
    # for tab in range(1,self.tabwidget.count() - 1):
    #     table = self.tabwidget.widget(tab).findChild(QTableWidget)
    #     if table.rowCount() > max_rows:
    #         max_rows = table.rowCount()

    # current_table.setRowCount(max_rows)
    # targetThickness = float(self.tabwidget.widget(0).targetThickness_input.text())
    # molarMass = float(self.tabwidget.widget(0).molarMass_input.text())
    # for i in range(max_rows):
    #     k = 2
    #     l = 0
    #     excited_state_energy = self.tabwidget.widget(1).findChild(QTableWidget).item(0,1).text()
    #     # print(excited_state_energy)
    #     for tab in range(1, self.tabwidget.count() - 1):
    #         #if self.tabwidget.widget(tab).findChild(QTableWidget).item(0,1).text() == excited_state_energy:  to be implemented later, checking if its the same state
    #         table = self.tabwidget.widget(tab).findChild(QTableWidget)
    #         val = table.item(i,7)
    #         err = table.item(i,8)
    #         if val is not None:
    #             volume = float(val.text())
    #             err = float(err.text())
    #             BCI_hit = float(self.tabwidget.widget(0).findChild(QTableWidget).item(l,1).text())
    #             BCI_scale = float(self.tabwidget.widget(0).findChild(QTableWidget).item(l,2).text())
    #             x_sec, error = cross_section_calculation(BCI_hit, BCI_scale, targetThickness, molarMass, volume, err)
    #             current_table.setItem(i,k, QTableWidgetItem(str(x_sec)))
    #             current_table.setItem(i,k + 1, QTableWidgetItem(str(error)))
    #         else:
    #             current_table.setItem(i,k, QTableWidgetItem(str(0.0)))
    #             current_table.setItem(i,k + 1, QTableWidgetItem(str(0.0)))
    #         l +=1
    #         k +=2
    # text_display.setPlainText("All possible cross-sections calculated!")

        # try:
        # except ValueError as e:
        #     QMessageBox.warning(self, "Input Error", str(e))
        # except Exception as e:
        #     QMessageBox.critical(self, "Error", f"An unexpected error occurred: {str(e)}")