classdef link
    properties
        h
        a
        order
        pose
        zero_pose
        alpha_
        distal
        c
    end
    
    methods
        function obj = link(a, h, c)
            obj.h = h;
            obj.a = a;
            obj.pose = [0,0,0,0,0,0];
            obj.zero_pose = [0,0,0,0,0,0];
            obj.alpha_ = 0;
            obj.c = c;
        end
        function obj = setZero(obj, zero_pose)
            obj.zero_pose = zero_pose;
        end
        function obj = linkPos(obj, alpha_)
            obj.alpha_ = alpha_;
            % figure out how the base pose changes
            obj.pose = poseFromMatrix(rightAction(obj.zero_pose, obj.a * obj.alpha_));
            obj.distal = poseFromMatrix(rightAction(obj.pose, obj.h));
        end
        function obj = drawLink(obj, ax)
            X = [obj.pose(1), obj.distal(1)];
            Y = [obj.pose(2), obj.distal(2)];
            Z = [obj.pose(3), obj.distal(3)];
            hold on
            % plots line
            plot3(ax, X, Y, Z, obj.c);
            % plots base
            plot3(ax, obj.pose(1), obj.pose(2), obj.pose(3), '^k');
            % plots distal
            plot3(ax, obj.distal(1), obj.distal(2), obj.distal(3), 'sk');
            hold off
        end
        function obj = drawDistalPose(obj, ax)
            plotPose(ax, obj.distal, 1);
        end
    end
    
    
    
end