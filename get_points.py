from matplotlib import pyplot as plt
import cv2
import numpy as np

sift = cv2.SIFT_create()
bf = cv2.BFMatcher()


def angle_with_x_axis(pi, pj):  # 公式在文件里解释
    """
    calculate θij:
        the angle this line subtends with the x-axis.
    """
    # get the difference between point p1 and p2
    x, y = pi[0] - pj[0], pi[1] - pj[1]

    if x == 0:
        return np.pi / 2

    angle = np.arctan(y / x)
    if angle < 0:
        angle += np.pi
    return angle


def midpoint(pi, pj):
    """
    get x and y coordinates of the midpoint of pi and pj
    """
    return (pi[0] + pj[0]) / 2, (pi[1] + pj[1]) / 2


class Mirror_Symmetry_detection:
    def __init__(self, image_path: str):
        # convert the image into the array/matrix
        self.image = self._read_color_image(image_path)

        self.reflected_image = np.fliplr(
            self.image)  # Flipped version of image

        # find the keypoints and descriptors with SIFT
        self.kp1, self.des1 = sift.detectAndCompute(self.image, None)
        self.kp2, self.des2 = sift.detectAndCompute(self.reflected_image, None)

    def _read_color_image(self, image_path):
        """
        convert the image into the array/matrix with oroginal color
        """
        image = cv2.imread(
            image_path)  # convert the image into the array/matrix
        b, g, r = cv2.split(image)       # get b,g,r
        image = cv2.merge([r, g, b])     # switch it to rgb

        return image

    def find_matchpoints(self):
        """
        Extracting and Matching a pair of symmetric features

        Matches are then sort between the features ki and the mirrored features mj
        to form a set of (pi,pj) pairs of potentially symmetric features.

        Ideally a keypoint at a certain spot on the object in original image should have a descriptor very similar to
        the descriptor on a point on the object in its mirrored version
        """
        # use BFMatcher.knnMatch() to get （k=2）matches
        matches = bf.knnMatch(self.des1, self.des2, k=2)
        # these matches are equivalent only one need be recorded
        matchpoints = [item[0] for item in matches]

        # sort to determine the dominant symmetries
        # Distance between descriptors. The lower, the better it is.
        matchpoints = sorted(matchpoints, key=lambda x: x.distance)

        return matchpoints

    def find_points_r_theta(self, matchpoints: list):
        """
        Get r, tehta of the midpoints of all pair of symmetric features
        """
        points_r = []  # list of r for each point
        points_theta = []  # list of theta for each point
        for match in matchpoints:

            # queryIdx is an index into one set of keypoints, (origin image)
            point = self.kp1[match.queryIdx]
            # trainIdx is an index into the other set of keypoints (fliped image)
            mirpoint = self.kp2[match.trainIdx]

            mirpoint.angle = np.deg2rad(
                mirpoint.angle)  # Normalise orientation
            mirpoint.angle = np.pi - mirpoint.angle
            # convert angles to positive
            if mirpoint.angle < 0.0:
                mirpoint.angle += 2 * np.pi

            # pt: coordinates of the keypoints x:pt[0], y:pt[1]
            # change x, not y
            mirpoint.pt = (
                self.reflected_image.shape[1] - mirpoint.pt[0], mirpoint.pt[1])

            # get θij: the angle this line subtends with the x-axis.
            theta = angle_with_x_axis(point.pt, mirpoint.pt)

            # midpoit (xc,yc) are the image centred co-ordinates of the mid-point of the line joining pi and pj
            xc, yc = midpoint(point.pt, mirpoint.pt)
            r = xc * np.cos(theta) + yc * np.sin(theta)

            points_r.append(r)
            points_theta.append(theta)

        return points_r, points_theta  # polar coordinates

    def draw_matches(self, matchpoints, top=10):
        """visualize the best matchs
        """
        img = cv2.drawMatches(self.image, self.kp1, self.reflected_image, self.kp2,
                              matchpoints[:top], None, flags=2)
        plt.imshow(img)
        plt.title("Top {} pairs of symmetry points".format(top))
        plt.show()

    def draw_hex(self, points_r: list, points_theta: list):
        """
        Visualize hex bins based on r and theta
        """
        # Make a 2D hexagonal binning plot of points r and theta
        image_hexbin = plt.hexbin(
            points_r, points_theta, bins=200, cmap=plt.cm.Spectral_r)
        plt.colorbar()  # add color bar
        plt.show()

    def find_coordinate_maxhexbin(self, image_hexbin, sorted_vote, vertical):
        """Try to find the x and y coordinates of the hexbin with max count
        """
        for k, v in sorted_vote.items():
            # if mirror line is vertical, return the highest vote
            if vertical:
                return k[0], k[1]
            # otherwise, return the highest vote, whose y is not 0 or pi
            else:
                if k[1] == 0 or k[1] == np.pi:
                    continue
                else:
                    return k[0], k[1]

    def sort_hexbin_by_votes(self, image_hexbin):
        """Sort hexbins by decreasing count. (lower vote)
        """
        counts = image_hexbin.get_array()
        ncnts = np.count_nonzero(np.power(10, counts))  # get non-zero hexbins
        verts = image_hexbin.get_offsets()  # coordinates of each hexbin
        output = {}

        for offc in range(verts.shape[0]):
            binx, biny = verts[offc][0], verts[offc][1]
            if counts[offc]:
                output[(binx, biny)] = counts[offc]
        return {k: v for k, v in sorted(output.items(), key=lambda item: item[1], reverse=True)}

    def draw_mirrorLine(self, r, theta, title: str):
        """
        Draw mirror line based on r theta polar co-ordinate
        """
        for y in range(len(self.image)):
            try:
                x = int((r - y * np.sin(theta)) / np.cos(theta))
                self.image[y][x] = 255
                self.image[y][x + 1] = 255
            except IndexError:
                continue

        # draw plot
        plt.imshow(self.image)
        plt.axis('off')
        plt.title(title)
        plt.show()

    def get_mid_line_points(self):
        matchpoints = self.find_matchpoints()

        # get r, tehta (polar coordinates) of the midpoints of all pair of symmetric features
        points_r, points_theta = self.find_points_r_theta(matchpoints)

        # find the best one with highest vote
        image_hexbin = plt.hexbin(points_r, points_theta,
                                  bins=200, cmap=plt.cm.Spectral_r)
        plt.close()

        sorted_vote = self.sort_hexbin_by_votes(image_hexbin)
        r, theta = self.find_coordinate_maxhexbin(
            image_hexbin, sorted_vote, vertical=False)

        points_J = np.arange(self.image.shape[0])
        points_I = (r - points_J * np.sin(theta)) // np.cos(theta)

        return np.stack((points_I, points_J), axis=1)


def test(filename='1_butterfly.png'):
    msd = Mirror_Symmetry_detection(f'./images/{filename}')

    points = msd.get_mid_line_points()
    print(np.max(points[:, 0]), np.min(points[:, 0]))
    print(np.max(points[:, 1]), np.min(points[:, 1]))
    plt.imshow(msd.image)
    plt.plot(points[:, 0], points[:, 1])
    plt.axis('off')
    plt.savefig(f'images/ans-{filename}')


if __name__ == "__main__":
    test("rotate-left-25.jpg")
    test("rotate-right-25.jpg")
