import rclpy
from rclpy.node import Node
from visualization_msgs.msg import Marker
from sheep_simulation_interfaces.msg import EntityPose
from sheep_simulation_interfaces.srv import EntitySpawn, Grid
import random
import math


class MasterSimulationNode(Node):
    def __init__(self):
        super().__init__('master_simulation_node')

        # simulation markers
        self.sheep_markers = {}
        self.sheep_marker_publisher = self.create_publisher(Marker, 'sheep_simulation/simulation/sheep_marker', 10)
        self.wolf_markers = {}
        self.wolf_marker_publisher = self.create_publisher(Marker, 'sheep_simulation/simulation/wolf_marker', 10)

        self.pen_marker_publisher = self.create_publisher(Marker, 'sheep_simulation/simulation/pen', 10)

        # Services
        self.grid_init_service = self.create_service(Grid, "sheep_simulation/grid", self.grid_init_callback)

        # clients to spawn entities
        self.sheep_spawn_client = self.create_client(EntitySpawn, 'sheep_simulation/sheep/spawn')
        while not self.sheep_spawn_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Waiting for sheep /spawn service...')
        self.sheep_spawn_request = EntitySpawn.Request()

        self.wolf_spawn_client = self.create_client(EntitySpawn, 'sheep_simulation/wolf/spawn')
        while not self.wolf_spawn_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Waiting for wolf /spawn service...')
        self.wolf_spawn_request = EntitySpawn.Request()

        # subcribe to entity position topics
        self.sheep_position_subscription = self.create_subscription(EntityPose, 'sheep_simulation/sheep/pose', self.sheep_position_callback, 10)
        self.wolf_position_subscription = self.create_subscription(EntityPose, 'sheep_simulation/wolf/pose', self.wolf_position_callback, 10)

        # create grid
        self.grid = self.create_grid(size=20.0)
        # self.grid_publisher = self.create_publisher(Grid, "sheep_simulation/grid", 10)
        # self.grid_publisher.publish(grid_msg)

        # create pens
        self.pen_size = 5.0
        self.pen_marker_publisher.publish(self.create_pen_marker("sheep_pen", size=self.pen_size))
        self.pen_marker_publisher.publish(self.create_pen_marker("wolf_pen1", size=self.pen_size / 2))
        self.pen_marker_publisher.publish(self.create_pen_marker("wolf_pen2", size=self.pen_size / 2))

        # spawn 6 sheep in 2 groups of 3
        self.spawn_sheep_group("group1", center_x=-10.0, center_y=10.0)
        self.spawn_sheep_group("group2", center_x=10.0, center_y=-10.0)

        # spawn 2 wolves
        self.spawn_wolf("wolf1", x=-20.0, y=20.0)
        self.spawn_wolf("wolf2", x=-20.0, y=-20.0)

    def create_grid(self, size):
        grid = [
            [-(size/2), (size/2)], #xmin, xmax
            [-(size/2), (size/2)]  #ymin, ymax
        ]

        return grid

    def spawn_sheep_group(self, group_name, center_x, center_y):
        for i in range(3):
            x = random.uniform(center_x - 2.0, center_x + 2.0)
            y = random.uniform(center_y - 2.0, center_y + 2.0)
            name = f"{group_name}_sheep{i+1}"
            self.spawn_sheep(name, x, y)

    def spawn_sheep(self, name):
    # Generate random spawn positions within the grid boundaries
        theta = random.uniform(0, 2 * math.pi)  # Random orientation

        # Create spawn request
        self.sheep_spawn_request.name = name
        self.sheep_spawn_request.x = x
        self.sheep_spawn_request.y = y
        self.sheep_spawn_request.theta = theta

        future = self.sheep_spawn_client.call_async(self.sheep_spawn_request)

        # Create marker for visualization
        marker = self.create_marker("sheep", name)
        marker.pose.position.x = x
        marker.pose.position.y = y
        marker.pose.position.z = 0.0
        marker.pose.orientation.z = math.sin(theta / 2)
        marker.pose.orientation.w = math.cos(theta / 2)

        self.sheep_markers[name] = marker
        self.sheep_marker_publisher.publish(marker)


    def spawn_wolf(self, name, x=0.0, y=0.0, theta=0.0):
        # spawn wolf inside pen
        x = random.uniform(self.grid[0][0], (self.grid[0][0] + self.pen_size/2))
        y = random.uniform((self.grid[1][1] - self.pen_size/2), self.grid[1][1])

        # create request
        self.wolf_spawn_request.name = name
        self.wolf_spawn_request.x = x
        self.wolf_spawn_request.y = y
        self.wolf_spawn_request.theta = 0.0

        future = self.wolf_spawn_client.call_async(self.wolf_spawn_request)

        # Create marker
        marker = self.create_marker("wolf", name)
        marker.pose.position.x = x
        marker.pose.position.y = y
        self.wolf_markers[name] = marker
        self.wolf_marker_publisher.publish(marker)

    def in_pen(self, x, y):
        return (x >= self.grid[0][1] - self.pen_size) and (y >= self.grid[1][1] - self.pen_size)

    def sheep_position_callback(self, response):
        if self.sheep_markers[response.name]:
            self.sheep_markers[response.name].pose.position.x = response.x
            self.sheep_markers[response.name].pose.position.y = response.y
            self.sheep_marker_publisher.publish(self.sheep_markers[response.name])

    def wolf_position_callback(self, response):
        if self.wolf_markers[response.name]:
            self.wolf_markers[response.name].pose.position.x = response.x
            self.wolf_markers[response.name].pose.position.y = response.y
            self.wolf_marker_publisher.publish(self.wolf_markers[response.name])

        if self.in_pen(response.x, response.y):
            self.get_logger().info(f"{response.name} in pen")

    def grid_init_callback(self, request, response):
        response.xmin = self.grid[0][0]
        response.xmax = self.grid[0][1]
        response.ymin = self.grid[1][0]
        response.ymax = self.grid[1][1]
        response.pensize = self.pen_size

        return response

    def create_marker(self, entity_type, name):
        marker = Marker()
        marker.header.frame_id = "map"
        marker.ns = name
        marker.id = 0
        marker.type = Marker.SPHERE
        marker.action = Marker.ADD
        marker.scale.x = 0.5
        marker.scale.y = 0.5
        marker.scale.z = 0.5
        marker.color.a = 1.0

        if entity_type == "sheep":  # Green for sheep
            marker.color.r = 0.0
            marker.color.g = 1.0
            marker.color.b = 0.0
        elif entity_type == "wolf":  # Red for wolf
            marker.color.r = 1.0
            marker.color.g = 0.0
            marker.color.b = 0.0

        return marker

    def create_pen_marker(self, name, size=10.0):
        marker = Marker()
        marker.header.frame_id = "map"
        marker.ns = name
        marker.id = 0
        marker.type = Marker.CUBE
        marker.action = Marker.ADD
        marker.scale.x = size
        marker.scale.y = size
        marker.scale.z = 0.1

        if name == "sheep_pen":
            marker.pose.position.x = self.grid[0][1] - (size/2)
            marker.pose.position.y = self.grid[1][1] - (size/2)
            marker.pose.position.z = 0.0
            marker.color.a = 0.5
            marker.color.r = 0.0
            marker.color.g = 0.0
            marker.color.b = 1.0
        elif name == "wolf_pen":
            marker.pose.position.x = self.grid[0][0] + (size/2)
            marker.pose.position.y = self.grid[1][1] - (size/2)
            marker.pose.position.z = 0.0
            marker.color.a = 0.5
            marker.color.r = 0.5
            marker.color.g = 0.0
            marker.color.b = 0.0

        return marker


def main(args=None):
    rclpy.init(args=args)
    node = MasterSimulationNode()
    rclpy.spin(node)
    rclpy.shutdown()
