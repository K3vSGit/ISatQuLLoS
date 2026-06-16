#########################################################################
######## Inter-Satellite Quantum Link Loss Simulations Software #########
#########################################################################

######################################
######### ISatQuLLoS IMPORTS #########
import numpy as np
import scipy.integrate
import scipy as sp
import matplotlib as mpl
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import plotly.graph_objects as go
import csv
import sys
import time
######################################
######################################
from PyQt5.QtCore import QObject, pyqtSignal


class Simulation(QObject):
    progressUpdated = pyqtSignal(int)
    #DataStatus = pyqtSignal(bool)
    stop = False

    def create3D_Plot(self, H1, H2, α, β, n):

        G = 6.6743*10**(-11)        #Gravitational constant in SI units
        M = 5.972*10**24            #Mass of the Earth in 'Kg'
        R = 6371*10**3              #Radius of the Earth in 'm'

        R1 = R + H1*10**3
        R2 = R + H2*10**3
        α = α*(np.pi/180)
        β = β*(np.pi/180)

        T1 = 2*np.pi*np.sqrt((R1**3)/(G*M))     #T = orbital period in 's'
        w1 = 2*np.pi/T1                         #w0 = angular frequency in 'rad/s'

        T2 = 2*np.pi*np.sqrt((R2**3)/(G*M))
        w2 = 2*np.pi/T2

        phi = 2*np.pi   #Reference azimuthal angle for both orbits.

        #Choose T to be the largest between T1 and T2 (for graphing/calculation purposes).
        if T1>T2:
            T = T1
        elif T2>T1:
            T = T2
        else:
            T = T1 

        #Create a time array for which to calculate the positions of the satellites at every second that ellapses.
        t_array = np.arange(0, n*T, 50) 

        theta1_array = w1*t_array
        theta2_array = w2*t_array

        x1 = R1*np.cos(phi)*np.sin(theta1_array - β)
        y1 = R1*np.sin(phi)*np.sin(theta1_array - β)
        z1 = R1*np.cos(theta1_array - β)

        x2 = R2*np.cos(phi - α)*np.sin(theta2_array)
        y2 = R2*np.sin(phi - α)*np.sin(theta2_array)
        z2 = R2*np.cos(theta2_array)

        #Make 3D plot to visualize the orbits.
        
        plot1 = go.Scatter3d(x=x1*10**(-3), y=y1*10**(-3), z=z1*10**(-3), mode='lines', name="Satellite 1", marker=dict(opacity=1, color='blue'), line_width=4)
        plot2 = go.Scatter3d(x=x2*10**(-3), y=y2*10**(-3), z=z2*10**(-3), mode='lines', name="Satellite 2", marker=dict(opacity=1, color='orange'), line_width=4)
        point0 = go.Scatter3d(x=[0], y=[0], z=[0], mode='markers', name="Earth Center", marker=dict(opacity=0.6, color='red', size=2))
        point3 = go.Scatter3d(x=[0], y=[0], z=[0], mode='markers', name="Sphere = Earth's surface (without atmosphere)", marker=dict(opacity=0.1, color='black', size=0.1))
        point1 = go.Scatter3d(x=[x1[0]*10**(-3)], y=[y1[0]*10**(-3)], z=[z1[0]*10**(-3)], mode='markers', marker=dict(opacity=0.8, color='blue', size=4), showlegend=False)
        point2 = go.Scatter3d(x=[x2[0]*10**(-3)], y=[y2[0]*10**(-3)], z=[z2[0]*10**(-3)], mode='markers', marker=dict(opacity=0.8, color='orange', size=4), showlegend=False)
    
        #Create sphere to represent Earth's surface as (trace0) plot0:
        u = np.linspace(0, 2 * np.pi, 100)
        v = np.linspace(0, np.pi, 100)
        x0 = R*10**(-3) * np.outer(np.cos(u), np.sin(v))
        y0 = R*10**(-3) * np.outer(np.sin(u), np.sin(v))
        z0 = R*10**(-3) * np.outer(np.ones(np.size(u)), np.cos(v))
        plot0 = go.Surface(x=x0, y=y0, z=z0, opacity=0.3, colorscale=[[0, '#272829'], [1, '#adb3b8']], hoverinfo='none', showscale=False) #, surfacecolor='grey'

        layout = go.Layout(showlegend=True, scene=go.Scene(
            xaxis=go.XAxis(title='X-Axis (km)'),
            yaxis=go.YAxis(title='Y-Axis (km)'),
            zaxis=go.ZAxis(title='Z-Axis (km)')))

        fig3D = go.Figure(data=(plot0, plot1, plot2, point0, point1, point2, point3), layout=layout)
        
        return fig3D


    def main(self, H1, H2, α, β, n, d_T, d_R, r_Tx_min, r_Rx_min, λ0, intLoss, I_Tx_Function0, K, t_slice, path):

        G = 6.6743*10**(-11)        #Gravitational constant in SI units
        M = 5.972*10**24            #Mass of the Earth in 'Kg'
        R = 6371*10**3              #Radius of the Earth in 'm'
        H0 = 100*10**3              #Height of high density atmosphere in 'm'

        R1 = R + H1*10**3
        R2 = R + H2*10**3
        α = α*(np.pi/180)
        β = β*(np.pi/180)

        T1 = 2*np.pi*np.sqrt((R1**3)/(G*M))     #T = orbital period in 's'
        w1 = 2*np.pi/T1                         #w0 = angular frequency in 'rad/s'
        v1 = w1*R1                              #v = orbital (tangential) velocity in 'm/s'

        T2 = 2*np.pi*np.sqrt((R2**3)/(G*M))
        w2 = 2*np.pi/T2
        v2 = w2*R2    

        phi = 2*np.pi   #Reference azimuthal angle for both orbits.

        λ = λ0*10**(-9) #Wavelength in 'm'.

        k = (2*np.pi)/λ
        r_Tx = d_T/2 #radius of transmitter aperture
        r_Rx = d_R/2 #radius of receiver aperture

        I_Tx = 1/(np.pi*((r_Tx)**2 - (r_Tx_min)**2))
        E_Tx = np.sqrt(I_Tx)

        #Choose T to be the largest between T1 and T2 (for graphing/calculation purposes).
        if T1>T2:
            T = T1
        elif T2>T1:
            T = T2
        else:
            T = T1 

        def satPos(n):
            #satPos(n) returns satellite position arrays limited by the chosen number of orbits "n".

            global RelDist_array, x1, x2, y1, y2, z1, z2, t_array

            #Create a time array for which to calculate the positions of the satellites at every second that ellapses.
            t_array = np.arange(0, n*T, 1) 

            theta1_array = w1*t_array
            theta2_array = w2*t_array

            x1 = R1*np.cos(phi)*np.sin(theta1_array - β)
            y1 = R1*np.sin(phi)*np.sin(theta1_array - β)
            z1 = R1*np.cos(theta1_array - β)

            x2 = R2*np.cos(phi - α)*np.sin(theta2_array)
            y2 = R2*np.sin(phi - α)*np.sin(theta2_array)
            z2 = R2*np.cos(theta2_array)

            #RelDist_array to calculate the relative distance between s1 and s2 at every point in time.
            RelDist_array = np.sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)

            return RelDist_array, x1, x2, y1, y2, z1, z1
        satPos(n)

        #Make 3D plot to visualize the orbits.
        def plot3D_orbits():
            plot1 = go.Scatter3d(x=x1*10**(-3), y=y1*10**(-3), z=z1*10**(-3), mode='lines', name="Satellite 1", marker=dict(opacity=1, color='blue'), line_width=4)
            plot2 = go.Scatter3d(x=x2*10**(-3), y=y2*10**(-3), z=z2*10**(-3), mode='lines', name="Satellite 2", marker=dict(opacity=1, color='orange'), line_width=4)
            point0 = go.Scatter3d(x=[0], y=[0], z=[0], mode='markers', name="Earth Center", marker=dict(opacity=0.6, color='red', size=2))
            point3 = go.Scatter3d(x=[0], y=[0], z=[0], mode='markers', name="Sphere = Earth's surface (without atmosphere)", marker=dict(opacity=0.1, color='black', size=0.1))
            point1 = go.Scatter3d(x=[x1[0]*10**(-3)], y=[y1[0]*10**(-3)], z=[z1[0]*10**(-3)], mode='markers', marker=dict(opacity=0.8, color='blue', size=4), showlegend=False)
            #point1 = go.Scatter3d(x=[x1[0]*10**(-3)], y=[y1[0]*10**(-3)], z=[z1[0]*10**(-3)], mode='markers', marker=dict(symbol='circle', opacity=0.8, color='blue', size=4), showlegend=False)
            point2 = go.Scatter3d(x=[x2[0]*10**(-3)], y=[y2[0]*10**(-3)], z=[z2[0]*10**(-3)], mode='markers', marker=dict(opacity=0.8, color='orange', size=4), showlegend=False)
    
            #Create sphere to represent Earth's surface:
            u = np.linspace(0, 2 * np.pi, 100)
            v = np.linspace(0, np.pi, 100)
            x0 = R*10**(-3) * np.outer(np.cos(u), np.sin(v))
            y0 = R*10**(-3) * np.outer(np.sin(u), np.sin(v))
            z0 = R*10**(-3) * np.outer(np.ones(np.size(u)), np.cos(v))
            plot0 = go.Surface(x=x0, y=y0, z=z0, opacity=0.3, colorscale=[[0, '#272829'], [1, '#adb3b8']], hoverinfo='none', showscale=False) #, surfacecolor='grey'

            layout = go.Layout(showlegend=True, scene=go.Scene(
                xaxis=go.XAxis(title='X-Axis (km)'),
                yaxis=go.YAxis(title='Y-Axis (km)'),
                zaxis=go.ZAxis(title='Z-Axis (km)')))

            fig3D = go.Figure(data=(plot0, plot1, plot2, point0, point1, point2, point3), layout=layout)
            return fig3D

        #L_max is the maximum displacement between S1 and S2 for which they have DLOS. 
        #L_max is  a single value in 'm'.
        L_max = np.sqrt(R1**2 - (R+H0)**2) + np.sqrt(R2**2 - (R+H0)**2) 

        #Create DLOS_array0 with relative distances between satellites while they have DLOS.
        #If they don't have DLOS, the values in the array are masked.
        DLOS_array0 = np.ma.masked_where(RelDist_array > L_max, RelDist_array)

        Masked_Index_array0 = np.ma.getmask(DLOS_array0) #getmaskarray to get array right away without the if statements!!
        if Masked_Index_array0.size == 1:
            Masked_Index_array = np.full_like(DLOS_array0, Masked_Index_array0)
        else:
            Masked_Index_array = Masked_Index_array0

        RUNTIME = len(Masked_Index_array)
        t_DLOS_array1 = np.empty([])
        t_DLOS_array2 = np.empty([])

        #Below we find the time interval for each pass between the satellites.
        if Masked_Index_array.size == 0:
            print("** WARNING: Plot of first pass is unavailable.")
        else:
            for i in range(RUNTIME):
                if Masked_Index_array[i] == False:
                    if i > 0:
                        if Masked_Index_array[i-1] == True:
                            t_insta = i
                            t_DLOS_array1 = np.append(t_DLOS_array1, t_insta)
                        elif Masked_Index_array[i-1] == False:
                            if RUNTIME == i+1:
                                t_DLOS_array2 = np.append(t_DLOS_array2, RUNTIME)
                            else: pass
                        else: pass
                    elif i == 0:
                        t_DLOS_array1 = np.append(t_DLOS_array1, 0)
                    else: pass

                elif Masked_Index_array[i] == True:
                    if i > 0:
                        if Masked_Index_array[i-1] == False:
                            t_insta = i-1
                            t_DLOS_array2 = np.append(t_DLOS_array2, t_insta)
                        elif Masked_Index_array[i-1] == True:
                            pass
                        else: pass
                    elif i == 0:
                        pass
                    else: pass
                else: pass

        t_DLOS_array1 = np.delete(t_DLOS_array1, 0)
        t_DLOS_array2 = np.delete(t_DLOS_array2, 0)
        t_DLOS_array_difference = t_DLOS_array2 - t_DLOS_array1

        #Below we calculate the total time for which satellites have DLOS within 'n' orbits.
        #t_DLOS is a single value measured in seconds.
        t_DLOS = 0
        if len(t_DLOS_array1) == 0:
            pass
        else:
            for i in range(len(t_DLOS_array_difference)):
                t_DLOS += t_DLOS_array_difference[i]

        t_DLOS_Percent = ((t_DLOS)/(RUNTIME))*100

        #Plot relative distance between s1 and s2 as a function of time:
        def plot0():
            Figure, SubPlot1 = plt.subplots(1,1, constrained_layout=True)
            #|Figure.suptitle("RSS as a function of time")

            SubPlot1.plot(t_array[::2], DLOS_array0[::2]*10**(-3), label="RSS with DLOS", c="blue")
            SubPlot1.plot(t_array, np.ma.masked_where(RelDist_array <= L_max, RelDist_array)*10**(-3), label="RSS without DLOS", c="red")
            #SubPlot1.set_title("RSS between S1 and S2 as a function of time")
            SubPlot1.set(xlabel = "Time (s)", ylabel = "RSS (km)")
            SubPlot1.legend(loc = 'best')
            SubPlot1.grid()
            return Figure
    
        #Here we calculate the minimum elevation angle A:
        if R1 <= R2:
            A = - (np.pi/2 - np.arcsin((R+H0)/R1))
        else:
            A = - (np.pi/2 - np.arcsin((R+H0)/R2))

        print("T = ", round(T/3600, 2), " hrs")
        if I_Tx_Function0 == "I_Tx":
            print("I_Tx = ", round(I_Tx, 2), "W/m^2")
        print("Percentage of time with DLOS in", n, "orbits = ", round(t_DLOS_Percent, 1), " %")

        print("""
########## Photon Detection Probability Calculations START ##########
""")
        #Below we create a plot of RSS vs Time for the first pass.
        NoData = False
        if t_DLOS == 0:
            NoData = True
            #self.DataStatus.emit(NoData) #We emit the staus of "NoData" as a boolean to the Logic.py file to figure out which plots exist and should be displayed.

        if NoData == False:
            #self.DataStatus.emit(NoData) #We emit the staus of "NoData" as a boolean to the Logic.py file to figure out which plots exist and should be displayed.
            print("First Pass time interval: ", round(t_DLOS_array_difference[0], 2), "s (=", round(t_DLOS_array_difference[0]/3600, 2), "hrs)")
            print("Minimum elevation angle: ", round(A*(180/np.pi), 2), "°")

            #####################################################################
            ###################### FIRST PASS CALCULATIONS ######################
            #####################################################################

            #'t_FP_array' and 'DLOS_FP_array' contain data for the first pass only.
            t_FP_array = t_array[int(t_DLOS_array1[0]):int(t_DLOS_array2[0])+1]
            DLOS_FP_array = DLOS_array0[int(t_DLOS_array1[0]):int(t_DLOS_array2[0])+1]

            #We make t_FP_array symmetric around t=0, at which point RSS is at a minimum,
            #by shifting t_FP_array by the time "t" of closest approach in t_FP_array (t_closest_approach).
            #NOTE: every element of t_FP_symmetric_array still matches with every element of DLOS_FP_array.
            # i.e. t_FP_symmetric_array[a] corresponds to DLOS_FP_array[a] which also corresponds to t_FP_array[a] as it should.
            t_closest_approach_index = int(np.abs(DLOS_FP_array).argmin())
            t_closest_approach = t_FP_array[t_closest_approach_index]
            t_FP_symmetric_array0 = t_FP_array - t_closest_approach

            #####################################################################
            ###################### Loss Simulations START #######################
            #####################################################################

            #Below we create a symmetric time array centered at t=0, defined in steps of K:
            #We first find the nearest integer to the bound, that is LESS than the bound itself.
            #Then for every integer below this number, we check if it is divisible by K, and take the first instance as the new bound.
            #Note: here we can't just shift the time axis, since the bounds must be specified.

            t_bound = False
            for i in np.abs(t_FP_symmetric_array0):
                if i % K == 0:
                    t_index = int(np.abs(t_FP_symmetric_array0 - i).argmin())
                    if i == np.abs(t_FP_symmetric_array0[t_index]):
                        t_bound = i #This is a positive value.
                        break
                    else:
                        continue
                else:
                    continue

            #Make the exeption to stop the program if no value within 'range(-t_max_int, t_max_int+1, 1)' is divisible by K.
            #(this only occurs if K > t_bound).
            if t_bound == False:
                print("** ERROR: 't_bound' does NOT exist for the given 't_FP_array' elements.")
                print("(No value within the time interval for which satellites have DLOS, is divisible by the specified K-value).")
                sys.exit()
            else:
                pass

            t_FP_symmetric_array = np.arange(-t_bound, t_bound+K, K)
            print("t_bound =", t_bound)
            if t_slice == 0:
                pass
            else:
                if t_slice > t_bound:
                    print("** WARNING: Entered value for 't_slice' is invalid. Full pass will be considered instead.")
                else:
                    #Here we slice t_FP_symmetric_array so that it goes from -t_slice to +t_slice:
                    t_index_start = np.where(t_FP_symmetric_array == -t_slice)[0][0]
                    t_index_stop = np.where(t_FP_symmetric_array == t_slice)[0][0]
                    t_FP_symmetric_array = t_FP_symmetric_array[t_index_start : t_index_stop+1]

    
            Detection_Probability_array = np.array([])
            DLOS_RSS_FP_array = np.array([])
            t_FP_array1 = np.array([])

            n = 10**4 #Integration resolution.
            ρ_array = np.linspace(r_Rx_min, r_Rx, n) #Array over which we do the integration for finding the PDP (at Rx).
            r_array = np.linspace(r_Tx_min, r_Tx, n) #Array for calculating the Fourier Transform (at Tx).

            #Here we edit the input function usch that R --> r_array.
            if "R" in I_Tx_Function0:
                I_T_Function = eval(I_Tx_Function0.replace("R", "r_array"))
                I_T_Function_array = I_T_Function
            else:
                I_T_Function = eval(I_Tx_Function0)
                I_T_Function_array = np.full_like(r_array, I_T_Function)
            E_T_Function = np.sqrt(I_T_Function)

            #Here we calculate the normalization constant:
            Integrand_array = 2*np.pi*r_array*I_T_Function_array
            Total_Power = sp.integrate.simpson(Integrand_array, r_array)
            print("Total Power = ", Total_Power) #<-- this value should always be 1.
            print("")
    
            j = 0 #this is defined to keep count of the number of iterations.
            
            # Preallocate arrays
            ɣ_array = np.empty(len(t_FP_symmetric_array)) #We calculate the elevation angle between S1 and S2 for every point in t_FP_symmetric_array0 (ɣ_array).
            E_R_array = np.empty((len(ρ_array),))
            I_R_array = np.empty_like(E_R_array)
            Integrand_array = np.empty_like(E_R_array)
            Detection_Probability_array = np.empty(len(t_FP_symmetric_array))
            DLOS_RSS_FP_array = np.empty_like(Detection_Probability_array)
            t_FP_array1 = np.empty_like(Detection_Probability_array)

            # Precompute constant values
            alpha_const = np.arccos((R1**2 + R2**2 - DLOS_FP_array**2) / (2 * R1 * R2))
            X_const = R2 * np.sin(np.pi / 2 - alpha_const)

            # Fourier Transform for calculating far field diffraction pattern of the electric field
            E_T_Function_reshaped = E_T_Function.reshape((-1, 1))
            r_array_reshaped = r_array.reshape((1, -1))
            ρ_array_reshaped = ρ_array.reshape((1, -1))

            
            for i, t in enumerate(t_FP_symmetric_array):
                L_index = np.abs(t_FP_symmetric_array0 - t).argmin()
                L = DLOS_FP_array[L_index]

                alpha = alpha_const[L_index]
                X = X_const[L_index]

            #Create loop to iterate over various RSS values.
            #After each iteration, we append the PDP to 'Detection_Probability_array'.
            for i, t in enumerate(t_FP_symmetric_array):
                #Check if stop_Simulation has been emitted from the Logic.
                if self.stop == True:
                    break
                L_index = np.abs(t_FP_symmetric_array0 - t).argmin()
                L = DLOS_FP_array[L_index]

                alpha = alpha_const[L_index]
                X = X_const[L_index]

                ɣ = np.empty(1)
                if R1 <= R2:
                    ɣ[R1 <= X] = np.arcsin((R2 * np.cos(alpha) - R1) / L)
                    ɣ[R1 > X] = -np.arcsin((R1 - R2 * np.sin(np.pi / 2 - alpha)) / L)
                else:
                    ɣ[R1 <= X] = np.arcsin((R1 * np.cos(alpha) - R2) / L)
                    ɣ[R1 > X] = -np.arcsin((R2 - R1 * np.sin(np.pi / 2 - alpha)) / L)

                ɣ_array[i] = ɣ

                Integrand_array = (k / L) * r_array_reshaped * E_T_Function_reshaped * sp.special.jv(0, (k * r_array_reshaped * ρ_array_reshaped) / L)
                I_R_array = np.abs(np.trapz(Integrand_array, r_array, axis=1))**2

                Integrand_array = 2 * np.pi * ρ_array * I_R_array
                Detection_Probability_scipy = np.trapz(Integrand_array, ρ_array) / Total_Power

                Detection_Probability_array[i] = Detection_Probability_scipy
                DLOS_RSS_FP_array[i] = L
                t_FP_array1[i] = t

                print("Iteration", int(j+1), "out of", len(t_FP_symmetric_array),": ", end="", flush=True)

                #Update the progress of the progress Bar of the interface.
                progress = int(round(((j + 1) / len(t_FP_symmetric_array)) * 100))
                self.progressUpdated.emit(progress)  # emit the signal

                j += 1
        
                print("Detection_Probability = ", round(Detection_Probability_scipy*100, 5), "%")


            Optical_Efficiency = 10**(-intLoss/10)
            System_PDP_array = (Detection_Probability_array)*Optical_Efficiency
            System_Loss_array = -10*np.log10(System_PDP_array)
            Link_Loss_array = -10*np.log10(Detection_Probability_array)

        #####################################################################
        ###################### Loss Simulations STOP ########################
        #####################################################################

        #Two conditions must be met in order to create the plots: 1) There the data to create them must exist; 2) We must not have stopped the simulations. 
        #If stop = True, we don't want to define any plots, since length of axes might be different
        #which would result in errors while creating the (empty) plots and thus crash the application.
        if self.stop == False:
            print("""
########### Photon Detection Probability Calculations STOP ###########
""")
            fig3D = plot3D_orbits()
            fig0 = plot0()

            if NoData == True:
                #If within "n" orbits there is NO first pass, make exception.
                print("** WARNING: No first pass exists within", int(round(n, 1)), "orbits!")
                #Check if data for the First Pass is unavailable/inexistant within 'n' orbits.
                print("** WARNING: Detection Probability plots unavailable (insufficient data).")
                print("** WARNING: No Time-Loss file available (insufficient data).")
            else:

                #Plot of FIRST PASS with RSS vs Time.
                def plot1():
                    Figure, SubPlot1 = plt.subplots(1,1, constrained_layout=True)
                    #Figure.suptitle("RSS = Relative Satellite Separation // DLOS = Direct Line of Sight")

                    string0 = "RSS with DLOS (First Pass)"
                    string1 = "RSS with DLOS (First Orbit)"
                    string2 = "α = " + str(round(α*(180/np.pi), 2)) + "°"
                    string3 = "β = " + str(round(β*(180/np.pi), 2)) + "°" #str(round(β0*100, 2)) + "% of 2π"
                    string4 = "H1 = " + str(round(H1, 1)) + " km"
                    string5 = "H2 = " + str(round(H2, 1)) + " km"

                    #plot0 is first pass + up to 1 orbit; plot1 is first pass ONLY.
                    plot1 = SubPlot1.plot(t_FP_symmetric_array0[::2], DLOS_FP_array[::2]*10**(-3), label=string0, c="blue", linewidth=2)
                    plot2 = SubPlot1.scatter(0, 0, label=string2, c="black", s=0.1)
                    plot3 = SubPlot1.scatter(0, 0, label=string3, c="black", s=0.1)
                    plot4 = SubPlot1.scatter(0, 0, label=string4, c="black", s=0.1)
                    plot5 = SubPlot1.scatter(0, 0, label=string5, c="black", s=0.1)

                    #SubPlot1.set_title("RSS as a function of time (first pass)")
                    SubPlot1.set(xlabel = "Time (s)", ylabel = "RSS (km)")
                    SubPlot1.legend(loc = 'best')
                    SubPlot1.grid()

                    return Figure

                #Plot of System Loss with RSS (FIRST PASS ONLY)
                def plot2():
                    Figure, SubPlot1 = plt.subplots(1,1, constrained_layout=True)
                    #Figure.suptitle("")

                    SubPlot1.scatter(DLOS_RSS_FP_array*10**(-3), System_Loss_array)
                    SubPlot1.set(xlabel = "DLOS RSS (km)", ylabel = "System Loss (dB)")
                    SubPlot1.grid()
                    return Figure

                #Plot of System Loss with Time (FIRST PASS ONLY)
                def plot3():
                    Figure, SubPlot1 = plt.subplots(1,1, constrained_layout=True)
                    #Figure.suptitle("")

                    SubPlot1.scatter(t_FP_symmetric_array, System_Loss_array)
                    SubPlot1.set(xlabel = "Time (s)", ylabel = "System Loss (dB)")
                    SubPlot1.grid()
                    return Figure
        
                #Plot of Link Loss with RSS (FIRST PASS ONLY)
                def plot4():
                    Figure, SubPlot1 = plt.subplots(1,1, constrained_layout=True)
                    Figure.suptitle("")

                    SubPlot1.scatter(DLOS_RSS_FP_array*10**(-3), Link_Loss_array)
                    SubPlot1.set(xlabel = "DLOS RSS (km)", ylabel = "Link Loss (dB)")
                    SubPlot1.grid()
                    return Figure

                #Plot of Link Loss with Time (FIRST PASS ONLY)
                def plot5():
                    Figure, SubPlot1 = plt.subplots(1,1, constrained_layout=True)
                    Figure.suptitle("")

                    SubPlot1.scatter(t_FP_symmetric_array, Link_Loss_array)
                    SubPlot1.set(xlabel = "Time (s)", ylabel = "Link Loss (dB)")
                    SubPlot1.grid()
                    return Figure
            
                fig1 = plot1()
                fig2 = plot2()
                fig3 = plot3()
                fig4 = plot4()
                fig5 = plot5()

                print("** Plots created succesfully.")


                ##Lastly we create a spreadsheet .csv file with all the relevant data.
                #We only want to create the .csv file if we didn't manually stop the calculations,
                #and the simulations have reached a natural end.

                #Because of how SatQuMA interprets the .csv file, we must flip the following arrays:
                t_FP_array1 = np.flip(t_FP_array1)
                ɣ_array = np.flip(ɣ_array)
                System_PDP_array = np.flip(System_PDP_array)

                fileName = "Time - Loss.csv"
                with open(path + '/' + fileName, 'w', newline='') as csvfile:
                    column1_Name ="Time (s)"
                    column2_Name ="Elevation (rad)"
                    column3_Name ="Sys_Efficiency"
                    fieldnames = [column1_Name, column2_Name, column3_Name]
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    for i, j, k in zip(t_FP_array1, ɣ_array, System_PDP_array):
                        writer.writerow({column1_Name: i, column2_Name: j, column3_Name: k})
                print("** Time - Loss file created succesfully, under '", path, "'.")
            print("")
            print("################### END OF PROGRAM ###################")

            
            #Return the figures as a list that can be passed to the Logic file.
            #Must only return the plots that were actually created.
            if NoData == True:
                return [fig3D, fig0]
            else:
                return [fig3D, fig0, fig1, fig2, fig3, fig4, fig5]
        else:
            #If stop = True, we want to print that we have stopped the simulations,
            #but we also need to reset the stop flag to False so it's ready to go again for the next run!! (this is done at the top of the code).

            print("""
#################################################
#############  Simulation STOPPED  ##############
#################################################
""")
        

        


#######################################################################################################
############################################# END OF CODE #############################################
#######################################################################################################
