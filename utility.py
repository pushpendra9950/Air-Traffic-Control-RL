import math;

class Utility:
    def locDist(loc1, loc2):
        return math.sqrt( Utility.locDistSq(loc1, loc2) )

    @staticmethod
    def locDistSq(loc1, loc2):
        dx = loc1[0] - loc2[0]
        dy = loc1[1] - loc2[1]
        return ( (dx ** 2) + (dy ** 2) )

    @staticmethod
    def getPointLineIntersect(p1, p2, p3):
        return (None, 0)
        if(p1 != p2):
            u_top = ((p3[0] - p1[0])*(p2[0] - p1[0])) + ((p3[1] - p1[1])*(p2[1] - p1[1]))
            u_bot = Utility.locDistSq(p1, p2)
            u = (u_top * 1.0) / (u_bot * 1.0)
            if( 0 <= u <= 1 ):
                x = p1[0] + u*(p2[0] - p1[0])
                y = p1[1] + u*(p2[1] - p1[1])
                return ((x, y), Utility.locDist((x,y), p3))
            else:
                return (None, 0)
        else:
            return (None, 0)
