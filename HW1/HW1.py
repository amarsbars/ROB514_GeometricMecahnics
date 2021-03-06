#!/usr/bin/python
# coding=utf-8

'''
1. Create 3 × 3 matrix representations of group elements from their (x, y, θ) parameters.

Operation		Transformation
---------		-------------------------
x				cos(theta)	-sin(theta)	x
y			=	sin(theta)	cos(theta)	y
theta			0			0			1


2. Compose group elements to produce new group elements.

Operation					Transformation
----------------------		--------------------------------
x			u				Operation1 * Operation2
y		+	v			=
theta		gamma


3. Multiply group elements by point locations to get the global positions of points in a
local frame.



'''




import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, Arc, Arrow, FancyArrowPatch, FancyArrow
from matplotlib.collections import PatchCollection
import pdb
import matplotlib
from moviepy.video.io.bindings import mplfig_to_npimage
import moviepy.editor as mpy
import copy
import seaborn as sns
sns.set()

class canvas(object):
	#just does the plotting
	def __init__(self,f,ax):
		self.f, self.ax = f,ax
		self.patches = []
		self.patches_old = []
		self.set_limits(-5,5)

	def getPatches(self, obj, clear=True):
		self.patches.extend(obj.patches)
		if clear: obj.patches = []

	def set_limits(self, low, high):
		self.low = low
		self.high = high
	
	def draw(self):
		[x.remove() for x in self.ax.get_children() if isinstance(x, matplotlib.collections.PatchCollection)]
		p = PatchCollection(self.patches, alpha=0.4, match_original=True)
		self.ax.add_collection(p)
		self.ax.set_xlim(self.low, self.high)
		self.ax.set_ylim(self.low, self.high)
		self.ax.set_xlabel('X'); self.ax.set_ylabel('Y')
		self.ax.set_aspect('equal')
		self.patches_old = self.patches
		self.patches = []


class triangle(object):
	# this is the object that will be rotated
	def __init__(self, base_pose = [0,0,0], scale = 1):
		self.patches = []
		self.pose = base_pose
		self.last_pose = base_pose
		self.large_vertices = np.array([[-1,-1], [-1, 1], [1, 0]]) * scale
		self.small_vertices = np.array([[0,1],[0,-1],[1,0]]) * scale

		self.large_vertices_base = np.array([[-1,-1], [-1, 1], [1, 0]]) * scale
		### to scale, subtract point to scale around, scale, add point to scale around
		scale_factor = 0.5 * scale
		scale_point = self.large_vertices_base[-1]
		self.small_vertices_base = (self.large_vertices_base - scale_point) * [scale_factor, scale_factor] + scale_point
		self.circle_color = [0.5, 0.5, 0.5]
		self.large_color  = [1,0,1]
		self.small_color = [0,1,1]

	def rotation_matrix(self, theta):
		c, s = np.cos(theta), np.sin(theta)
		R = np.matrix([[c, -s], [s, c]])
		return R

	def transformation_matrix(self, transform):
		# transform: x, y, theta
		c, s = np.cos(transform[2]), np.sin(transform[2])
		T = np.array([ [c,-s,transform[0]],
						[s,c,transform[1]],
						[0,0,1]])
		return T

	def pose_from_transformation_matrix(self, transformation_matrix):
		pose = np.zeros(3)
		pose[0] = transformation_matrix[0,2]
		pose[1] = transformation_matrix[1,2]
		pose[2] = np.arctan2(transformation_matrix[1,0], transformation_matrix[0,0])
		return pose

	def base_triangle(self, pose):
		self.large_vertices_base = self.transform_points(self.large_vertices_base, pose)
		self.small_vertices_base = self.transform_points(self.small_vertices_base, pose)

	def pts_to_pose(self, pts):
		pose = [np.append(p,1) for p in pts] #make it transformation matrix friendly
		return np.array(pose)

	def transform_points(self, points, pose):
		points_pose = self.pts_to_pose(points)
		trans = self.transformation_matrix(pose)
		new_pose = [np.dot(trans, p) for p in points_pose]
		new_points = [p[:2] for p in new_pose]
		return new_points

	def transform_pose(self, pose1, pose2):
		pts1 = self.pts_to_pose([pose1[:2]])
		new_pts1 = self.transform_points(pts1, pose2)
		pose1_new = new_pts1[0:2] + [pose1[2] + pose2[2]]
		pdb.set_trace()
		return pose1_new

	def large_triangle(self, center_pose):
		self.large_vertices = self.transform_points(self.large_vertices_base, center_pose)
		# self.large_vertices = self.left_action(self.large_vertices_base, center_pose)
		large_triangle = Polygon(self.large_vertices, True, alpha=0.4, color = self.large_color, edgecolor = 'k', linestyle = 'solid', linewidth = 2)
		self.patches.append(large_triangle)

	def small_triangle(self, center_pose):
		self.small_vertices = self.transform_points(self.small_vertices_base, center_pose)
		small_triangle = Polygon(self.small_vertices, True, alpha=0.4, color = self.small_color, edgecolor = 'auto', linestyle = 'solid', linewidth = 2)
		self.patches.append(small_triangle)

	def center(self, center_pose):
		center = Circle((center_pose[:2]),radius=0.1, color = self.circle_color, edgecolor = 'auto', alpha=0.4)
		self.patches.append(center)
		return center

	def left_action(self, current_pose, global_pose, move = True):
		combined_transformation = np.dot(self.transformation_matrix(global_pose), self.transformation_matrix(current_pose))
		pose = self.pose_from_transformation_matrix(combined_transformation)
		if move:
			c = self.move_to_pose(pose)
			return c
		else:
			return pose

	def right_action(self, current_pose, relative_pose):
		combined_transformation = np.dot(self.transformation_matrix(current_pose), self.transformation_matrix(relative_pose))
		pose = self.pose_from_transformation_matrix(combined_transformation)
		c = self.move_to_pose(pose)
		return c

	def move_to_pose(self, pose):
		self.last_pose = self.pose
		self.pose = pose
		self.large_triangle(pose)
		self.small_triangle(pose)
		c = self.center(pose)
		return c

	def inverse_action(self, pose):
		# undoing a transform = undoing translation and then undoing rotation
		transl_inv = self.transformation_matrix([-pose[0], -pose[1], 0])
		rot_inv = self.transformation_matrix([0,0,pose[2]])
		T = np.dot(transl_inv, rot_inv)
		return T

	def g_circ_right(self, g, g_dot): # body velocity
		# g is pose
		theta = g[2]
		inverse_lifted_action = [ 	[np.cos(theta), np.sin(theta), 0],
									[-np.sin(theta), np.cos(theta), 0],
									[0, 0, 1]
								]
		g_circ_right = np.dot(inverse_lifted_action, np.array(g_dot).reshape(-1,1))
		return g_circ_right

	def g_circ_left(self, g, g_dot): # spatial velocity
		inverse_lifted_action = [ 	[1, 0, g[1]],
									[0, 1, -g[0]],
									[0, 0, 1]
								]
		g_circ_left = np.dot(inverse_lifted_action, np.array(g_dot).reshape(-1,1))
		return g_circ_left

	def g_dot_from_g_circ_left(self, g, g_circ_left):
		lifted_action = [ 	[1, 0, -g[1]	],
							[0, 1, g[0]		],
							[0, 0, 1]
						]
		g_dot = np.dot(lifted_action, g_circ_left)
		return g_dot

	def drawVelocity(self, vel):
		# draws an arrow at current location (self.pose) in direction of x and y components
		# draw a circular arrow at current location to show rotation?
		translation_patch = Arrow(self.pose[0],self.pose[1], vel[0], vel[1])
		r = 0.5
		start = np.array([self.pose[0], self.pose[1]]) + r*np.array([np.cos(self.pose[2]), np.sin(self.pose[2])])
		end = np.array([self.pose[0], self.pose[1]]) + r*np.array([np.cos(self.pose[2] + vel[2]), np.sin(self.pose[2] + vel[2])])
		# rotation_patch = FancyArrowPatch(posA = start, posB = end, connectionstyle = 'arc3,rad=%s' %vel[2])
		# self.patches.append(rotation_patch)
		self.patches.append(translation_patch)

	def gdot_from_groupwisevelocity(self, act_type, g, g_circ):
		# page 86 of the book
		# g_dot = g_circ_left * g
		# g_dot = g * g_circ_right

		gtheta = g[2]
		gc = np.cos(g[2])
		gs = np.sin(g[2])
		gx = g[0]
		gy = g[1]
		G = [	[gc, -gs, gx],
				[gs,  gc, gy],
				[0,  0, 1]
			]
		gcirctheta = g_circ[2]
		gcircc = np.cos(gcirctheta)
		gcircs = np.sin(gcirctheta)
		gcircx = g_circ[0]
		gcircy = g_circ[1]
		GCIRC = [	[0, -gcirctheta, gcircx],
					[gcirctheta, 0, gcircy],
					[0, 0, 0]
				]

		if act_type == 'l':
			# g_dot = np.dot(GCIRC, G)
			s = np.sin
			c = np.cos
			# g_dot = [	[-s(g[2])*g_circ[2],	-c(g[2])*g_circ[2],		g_circ[0] - g[1]*g_circ[2]	],
			# 			[c(g[2])*g_circ[2],		-s(g[2])*g_circ[2],		g_circ[1] + g[0]*g_circ[2]	],
			# 			[0, 					0, 						0]
			# 		]
			# g_dot = np.array(g_dot)
			g_dot = self.g_dot_from_g_circ_left(g, g_circ)
		if act_type == 'r':
			g_dot = np.dot(G, GCIRC)
		# g_dot = self.pose_from_transformation_matrix(g_dot)
		return g_dot


	def spatialGeneratorFieldLeft(self, g, g_circ_left):
		g_dot = self.gdot_from_groupwisevelocity('l', g, g_circ_left)
		return g_dot

	def spatialGeneratorFieldRight(self, g, g_circ_right):
		g_dot = self.gdot_from_groupwisevelocity('r', g, g_circ_right)
		return g_dot

	def removeQuivers(self, ax):
		[x.remove() for x in ax.get_children() if isinstance(x, matplotlib.quiver.Quiver)]

	def drawSpatialGeneratorFieldLeft(self, ax, g_circ_left, theta = 0):
		self.removeQuivers(ax)
		R = np.arange(-5,5,0.5)
		X,Y = np.meshgrid(R, R)
		U = copy.deepcopy(X)
		V = copy.deepcopy(Y)
		for ix,x in enumerate(R):
			for iy,y in enumerate(R):
				g = np.array([x, y, theta])
				g_dot = self.spatialGeneratorFieldLeft(g, g_circ_left)
				U[ix, iy] = -g_dot[1]
				V[ix, iy] = -g_dot[0]
		Q = ax.quiver(X, Y, U, V, units='width')
		if (U > 0).any() or (V > 0).any():
			plt.draw()
			plt.pause(0.01)

	def drawSpatialGeneratorFieldRight(self, ax, g, g_circ_right):
		self.removeQuivers(ax)
		R = np.arange(-5,5,0.5)
		X,Y = np.meshgrid(R, R)
		U = copy.deepcopy(X)
		V = copy.deepcopy(Y)

		for ix,x in enumerate(R):
			for iy,y in enumerate(R):
				g_dot = self.g_dot_from_g_circ_right([x,y,g[2]], g_circ_right)
				U[ix, iy] = g_dot[0]
				V[ix, iy] = g_dot[1]
		Q = ax.quiver(X, Y, U, V, units='width')
		if (U > 0).any() or (V > 0).any():
			plt.draw()
			pdb.set_trace()



class motion_path(object):
	def __init__(self):
		self.patches = []

	def motion_path(self):
		arc1 = Arc((0,1), width=2, height=2, angle=0.0, theta1=-90.0, theta2=90.0)
		self.patches.append(arc1)
		arc2 = Arc((0,3), width=2, height=2, angle=180.0, theta1=-90.0, theta2=90.0)
		self.patches.append(arc2)

	def motion_path_pts(self, pts):
		r = 1
		pts_all = []
		theta_start = 0; theta_end = np.pi
		c = np.array([0,1])
		for theta in np.linspace(theta_start, theta_end, int(pts/2)):
			p = c + np.array([r*np.sin(theta), -r*np.cos(theta)])
			p = np.append(p, theta)
			pts_all.append(p)
		theta_start = 0; theta_end = -np.pi
		c = np.array([0,3])
		for theta in np.linspace(theta_start, theta_end, int(pts/2)):
			p = c + np.array([r*np.sin(theta), -r*np.cos(theta)])
			p = np.append(p, np.pi + theta)
			pts_all.append(p)
		# plt.plot(np.array(pts_all)[:,0], np.array(pts_all)[:,1])
		return pts_all

	def draw(self):
		# p = PatchCollection(patches, cmap=matplotlib.cm.jet, alpha=0.4)
		p = PatchCollection(self.patches, match_original=True)
		plt.xlim(-5, 5)
		plt.ylim(-5, 5)
		self.ax.add_collection(p)

class track_path(object):
	def __init__(self):
		self.patches = []

	def add_patch(self, patch):
		self.patches.append(patch,)

class makeMovie(object):
	def __init__(self):
		self.ax = plt.subplot(1,1,1)
		self.f = self.ax.get_figure()
		self.C = canvas(self.f,self.ax)
		# self.ax_list = plt.subplot(1,3,1)
		# f = self.ax_list[0].get_figure()
		# self.C = canvas(f,self.ax_list[0])
		self.T = triangle()
		self.T2 = triangle()
		self.path = self.MP = motion_path()
		self.path = self.MP.motion_path_pts(100)
		self.TP = track_path()
		self.TP2 = track_path()

	def single_triangle(self,t):
		cur_pose = self.path[int(t*10)]
		self.T.triangle(cur_pose)
		self.C.getPatches(self.T)
		self.C.draw()
		return mplfig_to_npimage(self.C.f)

	def two_triangle_with_path(self,t):
		h_local = [-2,-1,np.pi/4]
		base_pose = [0,0,0]
		cur_pose = self.path[int(t*10)]
		c_patch = self.T.left_action(base_pose, cur_pose)
		self.TP.add_patch(c_patch)
		#find local pose given new pose
		c_patch = self.T2.right_action(cur_pose, h_local)
		self.TP.add_patch(c_patch)
		self.C.getPatches(self.T)
		self.C.getPatches(self.T2)
		self.C.getPatches(self.TP, clear = False)
		self.C.draw()
		return mplfig_to_npimage(self.C.f)

# class line(object):
# 	#plots line between two centers
# 	def __init__(self):




if __name__ == '__main__':
	# f,ax = plt.subplots(1,1)
	# base_pose = [0,0,0]
	# C = canvas(f,ax)
	# T = triangle()
	# T2 = triangle()
	# TP = track_path()
	# MP = motion_path()
	# h_local = [-2,-2,np.pi/4]
	# path = MP.motion_path_pts(100)
	# for pose_new in path:
	# 	c1 = T.left_action(base_pose, pose_new)
	# 	c2 = T2.right_action(pose_new, h_local)
	# # 	#find local pose given new pose
	# 	TP.add_patch(c1)
	# 	TP.add_patch(c2)
	# 	C.getPatches(T)
	# 	C.getPatches(T2)
	# 	C.getPatches(TP, clear = False)
	# 	C.draw()
	# 	plt.draw()
	# 	plt.pause(0.001)
	# pdb.set_trace()



	MOV = makeMovie()
	animation = mpy.VideoClip(MOV.two_triangle_with_path, duration = 10)
	animation.write_gif("HW1.gif", fps = 20)

