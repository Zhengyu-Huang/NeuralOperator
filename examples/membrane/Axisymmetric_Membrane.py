import sys
import numpy as np
import math
import matplotlib.pyplot as plt
from Quadrature_Rule import gaussian_quad
from scipy.stats import truncnorm


class Membrane:
    def __init__(self, element_type, Coord, ur_r, density, alpha, pressure_load):

        '''
        ^ z
        |
        ---------------------  > r
        domain [X_l, X_r], 1 dim, each node has 2 freedom ur, uz
        Fix the left node ur = 0, and fix the z displacement of the right node uz = 0 , ur = self.end_disp_r
        Uniform conservative or noconservertive pressure load is applied
        Globally, elements or nodes are numbered from bottom to top and from left to right,
                  equations are numbered as ur_0, uz_0, ur_1, uz_1, ur_2, uz_2 ......
        Locally,  nodes are numbered from bottom to top and from left to right
                      Name            Description
                    -------         --------------
                    nDim            Number of Spatial Dimensions, is 1
                    nNodes          Number of nodes in the mesh
                    nElements       Number of elements in the mesh
                    nEdges          Number of edges in the mesh
                    nNodesElement   Number of nodes per element
                    nNodesEdge      Number of nodes per edge
                    nDoF            Number of DoF per node
                    nEquations      Number of equations to solve
                    ID              <nNodes x nDoF int> Array of global equation numbers, destination array (ID)
                                    ID(n,d) is the global equation number of node n's d freedom
                                    -1 means essential boundary condition,
                    EBC             <nNodes x nDoF int> EBC = 1 if the node's freedom is on Essential B.C.
                    NBC             <nEdgesElement x nElements int>  NBC = 1 if the element's edge is on the left boundary
                                                                     NBC = 2 if the element's edge is on the right boundary
                    IEN             <nNodesElement x nElements int>  Array of global node numbers
                                                                     IEN(i,e) is the global node id of element e's node i
                    LM             <nNodesElement*nDoF x nElements int> Array of global eq. numbers, location matrir (LM)
                                                              LM(d,e) is the global equation number of element e's d th freedom
                    g               <nNodes x nDoF double>	Essential B.C. Value at each node
                    d  F            <nequations  double>     displacements and RHS for all freedom
                    X Y u           <nNodes*nDoF double>     X coordinate, Y coordinate and displacements for all
        '''

        self.element_type = element_type
        self.set_para(Coord, ur_r, density, alpha, pressure_load)
        self.mesh_gen(Coord)
        self.boundary_cond()

        self.nEquations = (self.EBC == 0).sum()


    # def solve(self):
    #     '''
    #     solve for M ddot{d} = F
    #     :return:
    #     '''
    #     nElements = self.nElements
    #     nNodesElement = self.nNodesElement
    #     Coord = self.Coord
    #     IEN = self.IEN
    #     X_l = self.X_l

    #     nEquations = self.nEquations
    #     LM = self.LM

    #     element_type = self.element_type

    #     # d is the displacement on nodes
    #     d = np.zeros(nEquations)
    #     for e in range(nElements):
    #         for n in range(nNodesElement):
    #             # Get the R coordinate
    #             r = Coord[IEN[n, e], 0]

    #             # Initialize the radial dof uniformly
    #             # g = Params.endDispR
    #             if (LM[2 * n, e] != -1): ## warning depends on langrage, python -1, matlab 0
    #                d[LM[2 * n, e]] = (r -  X_l) * self.end_disp_r

    #     # Total number of iteration
    #     TotalIteration = math.ceil(self.pressure_load / 0.01) + 1

    #     # inner loop residual requirement
    #     eps = 1e-6

    #     # Inner loop maximal iteration step
    #     MaxIterstep = 100

    #     for Iterstep in range(0,TotalIteration + 1):

    #         self.current_pressure = Iterstep / TotalIteration * self.pressure_load

    #         # Newton's method
    #         NewtonIterstep = 0

    #         subiter_converge = False
    #         while not subiter_converge:

    #             NewtonIterstep = NewtonIterstep + 1

    #             [M, K, P, F] = self.assembly(element_type, d)

    #             RHS = F - P

    #             delta_d = np.linalg.solve(K, RHS)

    #             d = d + delta_d

    #             if (np.linalg.norm(RHS) < eps or NewtonIterstep > MaxIterstep):
    #                 if NewtonIterstep > MaxIterstep:
    #                     print('Newton iteration cannot converge')
    #                 subiter_converge = True
    #                 #print('displacement vector is ', d, ' ||d|| is ', np.linalg.norm(d))

    #     #convert to all freedom results
    #     nNodes = self.nNodes
    #     nDoF = self.nDoF
    #     EBC = self.EBC
    #     ID = self.ID
    #     g = self.g
    #     u = np.zeros((nNodes, nDoF))
    #     I = (EBC == 0)
    #     u[I] = d[ID[I]]
    #     u[~I] = g[~I]
    #     print(u)
    #     return u, d


    
    def solve(self, problem_type, TotalIteration, T):
        '''
        solve for M ddot{d} = F
        :return:
        '''
        nElements = self.nElements
        nNodesElement = self.nNodesElement
        Coord = self.Coord
        IEN = self.IEN
        X_l = self.X_l

        nEquations = self.nEquations
        LM = self.LM

        element_type = self.element_type

        # d is the displacement on nodes
        d = np.zeros(nEquations)
        for e in range(nElements):
            for n in range(nNodesElement):
                # Get the R coordinate
                r = Coord[IEN[n, e], 0]

                # Initialize the radial dof uniformly
                # g = Params.endDispR
                if (LM[2 * n, e] != -1): ## warning depends on langrage, python -1, matlab 0
                   d[LM[2 * n, e]] = (r -  X_l) * self.end_disp_r
        
        

        if problem_type == "Unsteady":
            v, a = np.zeros(nEquations), np.zeros(nEquations)
            d_arr, v_arr, a_arr = self.generalized_alpha_solve(d, v, a, T, TotalIteration)
        elif problem_type == "Steady":
            d_arr = self.steady_solve(d, MinTotalIteration=TotalIteration)
        else:
            print("problem_type = ", problem_type, " has not been implemented")

        #convert to all freedom results
        nNodes = self.nNodes
        nDoF = self.nDoF
        EBC = self.EBC
        ID = self.ID
        g = self.g
        u_arr = np.zeros((TotalIteration+1, nNodes, nDoF))
        I = (EBC == 0)
        for i in range(TotalIteration+1):
            u_arr[i, I] = d_arr[i, ID[I]]
            u_arr[i, ~I] = g[~I]
        return u_arr, d_arr
        
    def generalized_alpha_solve(self, d, v, a, T, TotalIteration, rho=0.0, maxiterstep=10, eps=1e-8):
        nEquations = self.nEquations
        d_arr = np.zeros((TotalIteration+1, nEquations)) ; d_arr[0,:] = d
        v_arr = np.zeros((TotalIteration+1, nEquations)) ; v_arr[0,:] = v
        a_arr = np.zeros((TotalIteration+1, nEquations)) ; a_arr[0,:] = a
        dt = T/TotalIteration

        for i in range(1,TotalIteration+1):
            d, v, a = self.generalized_alpha_solve_update(d, v, a, dt, rho=rho, maxiterstep=maxiterstep, eps=eps)
            d_arr[i,:], v_arr[i,:], a_arr[i,:] = d , v, a
            
        return d_arr, v_arr, a_arr
    

    def generalized_alpha_solve_update(self, d, v, a, dt, rho=0.0, maxiterstep=10, eps=1e-8):
        '''
        solve for M ddot{d} + F^int(d,v,a) = F^ext(d,v,a)
        :return:
        '''        
        alpha_m = (2*rho-1)/(1+rho)
        alpha_f = rho/(1+rho)
        
        
        beta2 = 0.5*(1 - alpha_m + alpha_f)**2
        gamma = 0.5 - alpha_m + alpha_f
        
        # inner loop residual requirement
        an = np.copy(a)
        self.current_pressure = self.pressure_load
        norm0 = np.inf
        Newtoniterstep, Newtonconverge = 0, False
        eta = 1.0
        while not Newtonconverge:
        
            Newtoniterstep += 1

            dn = (1 - alpha_f)*(d + dt*v + 0.5 * dt**2 * ((1 - beta2)*a + beta2*an)) + alpha_f*d
            vn = (1 - alpha_f)*(v + dt * ((1 - gamma)*a + gamma*an)) + alpha_f*v
            [M, K, P, F] = self.assembly(element_type, dn)
            res = np.dot(M , an *(1 - alpha_m) + alpha_m*a)  + P - F
            if Newtoniterstep==1:
                res0 = res 
 
            A = M*(1 - alpha_m) + (1 - alpha_f) * 0.5 * beta2 * dt**2 * K
            da = np.linalg.solve(A,res)


            while eta * np.linalg.norm(da) > norm0:
                eta /= 2.0
                print("reduce eta to ", eta)
            
            an -= eta*da

            if maxiterstep==1:
                break
     
            if (np.linalg.norm(res)< eps or np.linalg.norm(res)< eps*np.linalg.norm(res0) or Newtoniterstep > maxiterstep):
                if Newtoniterstep > maxiterstep:
                    print("Newton iteration cannot converge $(norm(res))")
                    Newtonconverge = True
                else:
                    Newtonconverge = True
            eta = min(1.0, 2*eta)
            norm0 = np.linalg.norm(da)

        dn = d + dt * v + dt**2/2 * ((1 - beta2) * a + beta2 * an)
        vn = v + dt * ((1 - gamma) * a + gamma * an)

        return dn, vn, an

    def steady_solve(self, d, MinTotalIteration=100, p_incr=0.05, maxiterstep=100, eps=1e-8):
        '''
        solve for P = F
        :return:
        '''
        # Total number of iteration
        TotalIteration = max(math.ceil(self.pressure_load / p_incr) + 1, MinTotalIteration)

        d_arr = np.zeros((TotalIteration+1, self.nEquations))
        d_arr[0,:] = d

        for Iterstep in range(1,TotalIteration+1):

            self.current_pressure = Iterstep / TotalIteration * self.pressure_load

            # Newton's method
            NewtonIterstep = 0

            subiter_converge = False
            while not subiter_converge:

                NewtonIterstep = NewtonIterstep + 1

                [M, K, P, F] = self.assembly(element_type, d)

                RHS = F - P

                delta_d = np.linalg.solve(K, RHS)

                d = d + delta_d

                if (np.linalg.norm(RHS) < eps or NewtonIterstep > maxiterstep):
                    if NewtonIterstep > maxiterstep:
                        print('Newton iteration cannot converge')
                    subiter_converge = True

            d_arr[Iterstep,:] = d

        return d_arr
    

    def set_para(self, Coord, ur_r, density, alpha, pressure_load):

        self.nDim = 1
        self.nDoF = 2

        # Radius of the membrane i.e.(X_l < r < L)
        self.X_l = Coord[0, 0]
        self.X_r = Coord[-1, 0]
        
        # fired r-displacement of the end node i.e.(r = L)
        self.end_disp_r = ur_r

        # Number of elements 
        self.Nr = Coord.shape[0]-1



        # final pressure load
        self.pressure_load = pressure_load
        self.current_pressure = pressure_load
        # pressure load type
        self.Pressure_Conservative = False

        #material property
        self.density = density
        self.alpha = alpha








    def mesh_gen(self, Coord):
        '''
        :param n_dim: 2
        :param geom: [Lx, Ly] computational domain is [0,Lx] [0,Ly]
        :param N: [Nr, Ny], Nr and Ny element in each direction
        :return:
        '''
        Nr = self.Nr
        X_l, X_r = self.X_l, self.X_r

        self.nNodesElement = 2
        self.nElements = Nr
        self.nNodes = Nr + 1

        self.Coord = Coord

        # construct  element nodes array
        # IEN(i,e) is the global node id of element e's node i
        IEN = np.zeros([self.nNodesElement, self.nElements], dtype='int')


        for ir in range(Nr):
            e = ir
            IEN[0, e] = ir
            IEN[1, e] = ir + 1


        self.IEN = IEN



    def boundary_cond(self, t = 0):
        '''
        Left nodes are fired
        :return:
        '''
        Coord = self.Coord
        nNodes = self.nNodes
        nDoF = self.nDoF
        Nr = self.Nr
        X_l, X_r = self.X_l, self.X_r

        X, Y = Coord[:,0], Coord[:,1]
        tol = 1.0e-8

        g = np.zeros((nNodes, nDoF))
        EBC = np.zeros((nNodes, nDoF))


        '''
        Define Essential boundary condition
        EBC = nNodes by nDoF matrir, 1 if the DOF of the Node is on the Essential B.C.
        '''

        
        for ir in range(Nr + 1):
            #Case If at r = X_l, set ur = 0
            if abs(X[ir] - X_l) < tol:
                print("set left boundary condition: ", ir)
                EBC[ir, 0] = 1
                g[ir, 0] = 0.

            # Case If at r = X_r, set uz = 0, ur = end_disp_r
            if abs(X[ir]- X_r) < tol:
                print("set right boundary condition: ", ir)
                EBC[ir, 0] = 1
                g[ir, 0] = self.end_disp_r
                EBC[ir, 1] = 1
                g[ir, 1] = 0.


        self.EBC = EBC
        self.g = g


        # construct destination array
        # ID(d,n) is the global equation number of node n's dth freedom, -1 means no freedom
        self.ID = np.zeros([self.nNodes, self.nDoF], dtype='int') - 1
        eq_id = 0
        for i in range(self.nNodes):
            for j in range(self.nDoF):
                if (self.EBC[i, j] == 0):
                    self.ID[i, j] = eq_id
                    eq_id += 1

        # LM(d,e) is the global equation number of element e's d th freedom
        self.LM = np.zeros([self.nNodesElement * self.nDoF, self.nElements], dtype='int')
        for i in range(self.nDoF):
            for j in range(self.nNodesElement):
                for k in range(self.nElements):
                    self.LM[j * self.nDoF + i, k] = self.ID[self.IEN[j, k], i]



    def assembly(self, element_type, d):
        #assert(element_type == 'AxisymmetricMembranePressure')
        nNodesElement = self.nNodesElement
        nDoF = self.nDoF
        nElements = self.nElements
        nEquations = self.nEquations
        LM = self.LM
        IEN = self.IEN
        EBC = self.EBC
        g = self.g


        #Allocate K and F
        M = np.zeros((nEquations, nEquations))
        K = np.zeros((nEquations, nEquations))
        P = np.zeros(nEquations)
        F = np.zeros(nEquations)

        for e in range(nElements):

            d_e = np.zeros(nNodesElement * nDoF)
            # check essential boundary condition
            n = IEN[:, e]
            for i in range(2): # node local id
                for j in range(2):  # freedom
                    if EBC[n[i], j] == 1:
                        d_e[2 * i + j] = g[n[i], j]

            PI = LM[:, e]
            I = (PI  != -1) ##todo warning
            PI = PI[I]
            d_e[I] = d[PI]


            m_e, k_e, p_e, f_e = self.constitutive_law(e, d_e)
            f_g = np.zeros(nNodesElement * nDoF)
            f_h = np.zeros(nNodesElement * nDoF)

            # Step 3b: Get Global equation numbers
            PI = LM[:, e]

            # Step 3c: Eliminate Essential DOFs
            I = (PI >= 0)
            PI = PI[I]

            # Step 3d: Insert m_e, k_e, f_e, f_g, f_h
            M[np.ix_(PI, PI)] += m_e[np.ix_(I, I)]
            K[np.ix_(PI, PI)] += k_e[np.ix_(I, I)]
            P[PI] += p_e[I]
            F[PI] += f_e[I] + f_g[I] + f_h[I]

        return M, K, P, F


    def constitutive_law(self, e, d_e):
        '''
        The constitutive law of the incompressible axisymmetric membrane
        Its energy function is defined on the undeformed domain,
              W = int_X_l^X_r W(lambda_1, lambda_2) 2 pi R(x) T(x) dx + V
        here T(x) is the initial thickness and R(x) is the radius
        W is the potential function, depends on the principle stretches lambda_1, lambda_2, and lambda_3,
        The incompressibility is lambda_1*lambda_2*lambda_3 = 1
        here lambda_1 = ds*/ds = sqrt(dz**2 + dr**2)/sqrt(dZ**2 + dR**2) , the length stretch ;
             lambda_2 = 2 pi r/ 2 pi R, the radius stretch ;
             lambda_3 = t / T, the thickness stretch .
        V is the external force potential
        W is needed to be learned by Neural network, especially P1 = dW/dlambda1 and P2 = dW/dlambda2
        :param e:
        :return:
        '''
        nNodesElement = self.nNodesElement
        nDoF = self.nDoF
        m_e = np.zeros([nNodesElement * nDoF, nNodesElement * nDoF])
        k_e = np.zeros([nNodesElement * nDoF, nNodesElement * nDoF])
        p_e = np.zeros(nNodesElement * nDoF)
        f_e = np.zeros(nNodesElement * nDoF)
        

        n_points = 3
        [xi, w] = gaussian_quad(n_points)

        alpha = self.alpha[e]

        # Loop for Gaussian Quadrature
        for i in range(n_points):
            '''
            For P we need dW:
            dW = int_X_l^X_r dW(lambda_1, lambda_2) 2 pi R(x) T(x) dx + V
               = loop each element:   sum_e int_e dW(lambda_1, lambda_2) 2 pi R(x) T(x) dx
            On each element: the parent element Pe is -1 <= xi <= 1
            int_e dW(lambda_1, lambda_2) 2 pi R(x) T dx
            =  int_Pe dW(lambda_1, lambda_2) 2 pi R(x(xi)) T M(xi) dxi here M = |dx/dxi|
            =  2piT * int_Pe dW(lambda_1, lambda_2) R(x(xi)) M(xi) dxi
            =  dW(lambda_1, lambda_2) = dW/dlambda_1 dlambda_1 + dW/dlambda_2 dlambda_2 (P1=dW/dlambda_1 P2 = dW/dlambda_2)
                                      = P1 dlambda_1 + P2 dlambda_2
                                      = [dur_0, duz_0, dur_1, duz_1] Ba.T [P1, P2].T
            Ba = dlambda_1/dur_0, dlambda_1/duz_0, dlambda_1/dur_1, dlambda_1/duz_1
                 dlambda_2/dur_0, dlambda_2/duz_0, dlambda_2/dur_1, dlambda_2/duz_1
            For K we need ddW:
            dW = int_X_l^X_r ddW(lambda_1, lambda_2) 2 pi R(x) T(x) dx + V
               = loop each element:   sum_e int_e ddW(lambda_1, lambda_2) 2 pi R(x) T(x) dx
            On each element: the parent element Pe is -1 <= xi <= 1
            int_e dW(lambda_1, lambda_2) 2 pi R(x) T dx
            =  int_Pe ddW(lambda_1, lambda_2) 2 pi R(x(xi)) T M(xi) dxi here M = |dx/dxi|
            =  2piT * int_Pe ddW(lambda_1, lambda_2) R(x(xi)) M(xi) dxi
            =  ddW(lambda_1, lambda_2) = P1 ddlambda_1 + P2 ddlambda_2 + dP1 dlambda_1 + dP2 dlambda_2
                                       = P1 ddlambda_1 + P2 ddlambda_2
                                         + [dlambda_1, dlambda_2] ddW [dlambda_1 + dP2 dlambda_2].T
            P1 ddlambda_1 + P2 ddlambda_2 = du [P1 ddlambda_1/ddu  + P2 ddlambda_2/ddu] du
                                          = du  P1 ddlambda_1/ddu du
            [dlambda_1, dlambda_2] ddW [dlambda_1 + dP2 dlambda_2].T = du Ba.T D_mat Ba du.T
            here D_mat = ddW = [ddW/dlambda_1**2, ddW/dlambda_1 dlambda_2],[ddW/dlambda_1dlambda_2, ddW/dlambda_2**2]
            So: learning need to predict W, P1, P2, and D_mat, and P1 in D_geom
            '''
            Na, Na_xi, Ba, ue, ue_xi, X_xi, R, M, lambda_1, lambda_2 = self.sample_shape_functions(xi[i], e, d_e)

            P1, P2, D_geom, D_mat = self.geom_and_mat_matricies(lambda_1, lambda_2, alpha)
            
            m_e += self.density * R * M * np.dot(Na.T, Na)*w[i]

            p_e += R * M * np.dot(Ba.T, np.array([P1,P2]))*w[i]

            k_e += (np.dot(Ba.T, np.dot(D_geom + D_mat, Ba)) + P1 / (lambda_1 * M ** 2) * np.dot(Na_xi.T,Na_xi)) \
                   * R * M * w[i]

            # conservative pressure load contribution (load in the undeformed domain)
            if self.Pressure_Conservative:
                f_e += self.current_pressure * np.dot(Na.T , np.array([-X_xi[1], X_xi[0]])) * R * w[i]
            else:

                # non - conservative (load on the undeformed domain)
                r = ue[0]
                r_xi = ue_xi[0]
                z_xi = ue_xi[1]
                f_e += self.current_pressure * np.dot(Na.T , np.array([-z_xi, r_xi])) * r * w[i]


                k_e_press = np.zeros([4, 4])
                for a in range(2):
                    for b in range(2):
                        k_e_press[2 * a: 2 * a + 2, 2 * b: 2 * b + 2] = \
                            self.current_pressure * np.array([[Na[0, 2 * a] * z_xi * Na[0, 2 * b], Na[0, 2 * a] * r * Na_xi[0, 2 * b]],
                                                              [-Na[0, 2 * a] * r * Na_xi[0, 2 * b] - Na[0, 2 * a] * r_xi * Na[0, 2 * b], 0]])


                k_e = k_e + k_e_press * w[i]

        return m_e, k_e, p_e, f_e


    def geom_and_mat_matricies(self, lambda_1, lambda_2 , alpha):
        '''
        :param self:
        :param lambda_1: stretche
        :param lambda_2: stretche
        :param Params:
        :return: the first Piola - Kirchhoff stress P1 and P2
                 the geometric and material stiffness matricies
                 <2 by 2> D_geom
                 <2 by 2> D_mat
                    dW
        '''



        lambda_3 = 1 / (lambda_1 * lambda_2)

        # P1 = dW / dlambda_1
        P1 = 2 / lambda_1 * (1 + alpha * lambda_2 ** 2) * (lambda_1 + lambda_3) * (lambda_1 - lambda_3)
        # P2 = dW / dlambda_2
        P2 = 2 / lambda_2 * (1 + alpha * lambda_1 ** 2) * (lambda_2 + lambda_3) * (lambda_2 - lambda_3)

        # W11 = ddW / dlambda_1 ^ 2
        W11 = -3 * P1 / lambda_1 + 8 * (1 + alpha * lambda_2**2)

        # W12 = ddW / dlambda_1dlambda_2
        W12 = 4 * alpha / lambda_3 + 4 * lambda_3**3

        # W22 = ddW / dlambda_2 ^ 2
        W22 = -3 * P2 / lambda_2 + 8 * (1 + alpha * lambda_1**2)

        D_geom = np.array([[-P1 / lambda_1, 0.0], [0.0, 0.0]])

        D_mat = np.array([[W11, W12],[W12, W22]])

        return P1, P2, D_geom, D_mat


    def sample_shape_functions(self, xi, e, d_e):
        '''
        :param self:
        :param xi: double, the gaussian point -1 <= xi <= 1
        :param e:  int, element id
        :param d_e: 4 double array,  element freedom displacements, ur_0, uz_0, ur_1, uz_1
        :return:
        Na:         the shape function matrix <2 by 4>,
        Na_xi :     its LOCAL derivative < 2 by 4>,
        ue    :     deformed position  <2 by 1>
        ue_xi :     D deformed position/ D xi <2 by 1>
        Ba:     matrix that will be used to compute  the local tangent operator.
                dlambda_1/dur_0, dlambda_1/duz_0, dlambda_1/dur_1, dlambda_1/duz_1
                dlambda_2/dur_0, dlambda_2/duz_0, dlambda_2/dur_1, dlambda_2/duz_1
        R:      undeformed position
        M:      ||dx/dxi||
        '''
        # Step 1: Access Global Variables
        IEN = self.IEN
        Coord = self.Coord

        Na = np.array([[(1 - xi) / 2, 0, (1 + xi) / 2, 0],
                       [0, (1 - xi) / 2, 0, (1 + xi) / 2]])
        Na_xi = np.array([[-1. / 2., 0, 1. / 2., 0],
                          [0, -1. / 2., 0, 1. / 2.]])

        X0 = Coord[IEN[:, e],:]
        X0 = np.reshape(X0, -1)
        R = np.dot(Na[0,:], X0)
        M = np.linalg.norm(np.dot(Na_xi , X0))
        X_xi = np.dot(Na_xi , X0)

        ue = np.dot(Na , d_e + X0)
        ue_xi = np.dot(Na_xi , d_e + X0)

        lambda_1 = np.linalg.norm(ue_xi) / M
        lambda_2 = ue[0] / R

        r_xi = ue_xi[0]
        z_xi = ue_xi[1]

        Ba = np.zeros([2, 4])
        Ba[0,:] = r_xi / (lambda_1 * M ** 2) * Na_xi[0,:] + z_xi / (lambda_1 * M ** 2) * Na_xi[1,:]
        Ba[1,:] = Na[0,:] / R

        return Na, Na_xi, Ba, ue, ue_xi, X_xi, R, M, lambda_1, lambda_2




    def visualize(self, u, ax, init_state=True, label=""):
        '''
        :param d: displacement at each node
        :return:
        '''
        X, Y = self.Coord[:,0], self.Coord[:,1]

        if init_state:
            ax.plot(X, Y, "--", color="r", label="Initial"+label)

        ax.plot(X + u[:,0], Y+ u[:,1], "-o", color="black", fillstyle="none", markersize=5, label="Inflated"+label)
        ax.legend()











if __name__ == '__main__':
    
    element_type = "Mooney_Rivlin_Hyperelastic"

    #Step 1. define the initial shape.
    #        it is a curve between Coord_l to Coord_r with Coord_r[1]=0
    X_l, X_r,  Nr = 0.2, 1.0, 50
    R = np.linspace(X_l, X_r, num = Nr + 1)
    # Z = np.zeros(Nr + 1)
    Z = np.linspace(0.2, 0.0, num = Nr + 1)
    Coord = np.vstack((R, Z)).T

    #Step 2. define the initial stretch
    #        the r-displacement of the right hand side of the curve
    ur_r = 0.0

    #Step 3. define pressure load
    pressure_load = 1.0

    #Step 4. define material property
    density = 1.0
    alpha = np.zeros(Nr)
    alpha[0:Nr//2] = 0.1
    alpha[Nr//2:] = 0.2

    model = Membrane(element_type, Coord, ur_r, density, alpha, pressure_load)

    

    # problem_type = "Steady"
    # TotalIteration, T = 500, np.inf

    problem_type = "Unsteady"
    TotalIteration, T = 1000, 10.0
    u_arr, d_arr = model.solve(problem_type, TotalIteration, T)

    for i in range(0, TotalIteration+1, 1):

        fig, ax = plt.subplots(1, 1, figsize=(6, 6))
        model.visualize(u_arr[i,:,:], ax, init_state=True, label="")
        fig.savefig("Figs/Membrane_shape%d.png"%(i))