import numpy as np

class Satellite:
    EARTH_RADIUS = 6371

    # State Thresholds
    DELAY_LOW = 200 #*5 # Max distance for low LATENCY
    DELAY_MEDIUM = 1000 #*5 # Max distance for medium LATENCY, anything above is high
    CONGESTION_LOW = 1 # Max connections for low congestion,
    CONGESTION_MEDIUM = 3 # Max connections for medium congestion, anything above is high
    CONGESTION_HIGH = 5 # Can't accept connections after this value

    ALPHA = 0.50 # learning rate
    GAMMA = 0.95 # discount factor
    EPSILON = 0.2  # exploration rate

    # Class variables for precomputed matrices
    satellites = []
    visibility_matrix = [[]]
    distance_matrix = [[]]
    latency_matrix = [[]]

    index = 0

    def __init__(self, longitude, latitude, height, speed):
        self.longitude = longitude
        self.latitude = latitude
        self.height = height
        self.speed = speed  # Speed in degrees per update cycle
        self.connections = [] # Number active connections 
        self.Q = {}
        self.satellites # Other satellites in the constellation network
    
    def update_position(self): # Moves satellite 1 speed increment
        self.longitude = (self.longitude + self.speed) % 360  # Wrap longitude within 0-360 degrees

    def get_cartesian_coordinates(self):
        # Convert spherical (longitude, latitude, height) to Cartesian (x, y, z)
        r = 1 + self.height  # Assume base radius is 1
        lon = np.radians(self.longitude)
        lat = np.radians(self.latitude)
        x = r * np.cos(lat) * np.cos(lon)
        y = r * np.cos(lat) * np.sin(lon)
        z = r * np.sin(lat)
        return np.array([x, y, z])

    def out_of_sight(self, other):
        # Checks if the other satellite is out of sight
        vector_self = self.get_cartesian_coordinates()
        vector_other = other.get_cartesian_coordinates()
        
        # Normalize vectors
        vector_self_normalized = vector_self / np.linalg.norm(vector_self)
        vector_other_normalized = vector_other / np.linalg.norm(vector_other)
        
        # Compute dot product
        dot_product = np.dot(vector_self_normalized, vector_other_normalized)
        
        # Compute angle in degrees
        angle = np.degrees(np.arccos(dot_product))
        
        # If angle > 90 degrees, the other satellite is out of sight
        return angle > 75

    def calculate_distance(self, other):
        # Convert latitudes and longitudes to radians
        lat1, lon1 = np.radians(self.latitude), np.radians(self.longitude)
        lat2, lon2 = np.radians(other.latitude), np.radians(other.longitude)
        
        # Haversine formula
        delta_lat = lat2 - lat1
        delta_lon = lon2 - lon1
        a = np.sin(delta_lat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(delta_lon / 2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        
        # Adjust for the altitude of satellites
        r1 = self.EARTH_RADIUS + self.height
        r2 = self.EARTH_RADIUS + other.height
        
        # Use the average radius for great circle distance
        r_avg = (r1 + r2) / 2
        
        # Arc distance
        distance = r_avg * c
        return distance

    def check_latency(self, other):
        # distance = self.calculate_distance(other)
        # if distance <= self.DELAY_LOW:
        #     return 'low'
        # elif distance <= self.DELAY_MEDIUM:
        #     return 'medium'
        # else:
        #     return 'high'
        if(type(other) == int):
            return Satellite.latency_matrix[self.index][other]
        elif(type(other) == Satellite):
            return Satellite.latency_matrix[self.index][other.index]

    def check_congestion(self):
        if len(self.connections) <= self.CONGESTION_LOW:
            return 'low'
        elif len(self.connections) <= self.CONGESTION_MEDIUM:
            return 'medium'
        else:
            return 'high'

    def get_state(self, endpoint_satellite):
        delay_state = self.check_latency(endpoint_satellite)
        congestion_state = self.check_congestion()
        return (delay_state, congestion_state)

    def get_possible_actions(self):
        possible_actions = []

        # for sat in self.satellites:
        #     if not self.out_of_sight(sat) and sat != self:
        #         possible_actions.append(sat)

        for i, visible in enumerate(Satellite.visibility_matrix[self.index]):
            if visible and i != self.index:
                sat = Satellite.satellites[i]
                # Check if satellite is congested (max number connections)
                if len(sat.connections) < self.CONGESTION_HIGH:
                    possible_actions.append(sat)
        return possible_actions

    def get_reward(self, state, is_final=False, relay_penalty=-1):
        # Calculate reward for given state
        delay_state, congestion_state = state
        delay_reward = {'low': -1, 'medium': -5, 'high': -10}[delay_state]
        congestion_reward = {'low': -1, 'medium': -5, 'high': -10}[congestion_state]
        total_reward = delay_reward + congestion_reward - relay_penalty
        if is_final: # Reward for reaching the endpoint
            total_reward += 100
        return total_reward

    def update_q_value(self, state_current, action_current, reward, state_next):
        # Q(s, a) <- Q(s, a) + \alpha * [r + \gamma * max_a(Q(s_next, a')) - Q(s, a)]
        max_q_next = max([self.Q.get((state_next, a), 0) for a in self.get_possible_actions()], default=0)
        q_current = self.Q.get((state_current, action_current), 0)
        q_new = q_current + self.ALPHA * (reward + self.GAMMA * max_q_next - q_current)
        self.Q[(state_current, action_current)] = q_new

    def choose_action(self, state_current, possible_actions):
        if np.random.rand() < self.EPSILON: # Exploration
            return np.random.choice(possible_actions)
        else: # Exploitation
            q_values = [self.Q.get((state_current, a), 0) for a in possible_actions]
            max_q = max(q_values)
            best_actions = [a for a, q in zip(possible_actions, q_values) if q == max_q]
            return np.random.choice(best_actions)


class Constellation:

    def precompute_matrices(self, satellites):
        self.satellites = satellites
        num_satellites = len(self.satellites)
        
        Satellite.satellites = satellites
        Satellite.visibility_matrix = np.zeros((num_satellites, num_satellites), dtype=bool)
        Satellite.distance_matrix = np.zeros((num_satellites, num_satellites))
        Satellite.latency_matrix = np.empty((num_satellites, num_satellites), dtype=object)

        # Assign index to each satellite 
        for i, satellite in enumerate(self.satellites):
            satellite.index = i

        # Loop through every satellite pair to pre-compute state
        for a in range(num_satellites):
            for b in range(num_satellites):
                if a == b: # Same satellite
                    Satellite.visibility_matrix[a][b] = False
                    Satellite.distance_matrix[a][b] = 0
                    Satellite.latency_matrix[a][b] = 'low'
                else:

                    sat1 = self.satellites[a]
                    sat2 = self.satellites[b]

                    # Compute visibility
                    Satellite.visibility_matrix[a][b] = not sat1.out_of_sight(sat2)

                    # Compute distance
                    distance = sat1.calculate_distance(sat2)
                    Satellite.distance_matrix[a][b] = distance

                    if distance <= Satellite.DELAY_LOW:
                        latency = 'low'
                    elif distance <= Satellite.DELAY_MEDIUM:
                        latency = 'medium'
                    else:
                        latency = 'high'

                    Satellite.latency_matrix[a][b] = latency

    def train_iteration(self, start_satellite, end_satellite):
        current_satellite = start_satellite
        path = [current_satellite]
        while current_satellite != end_satellite:
            state_current = current_satellite.get_state(end_satellite.index)
            possible_actions = current_satellite.get_possible_actions()
            if not possible_actions:
                # No possible actions; terminate the episode
                break

            action_current = current_satellite.choose_action(
                state_current, possible_actions
            )
            next_satellite = action_current

            # Simulate adding a connection (increasing congestion)
            current_satellite.connection_count += 1
            next_satellite.connection_count += 1

            is_final = next_satellite == end_satellite
            state_next = next_satellite.get_state(end_satellite.index)
            reward = current_satellite.get_reward(state_next, is_final)

            current_satellite.update_q_value(
                state_current, action_current, reward, state_next
            )

            # Simulate removing the connection (decreasing congestion)
            current_satellite.connection_count -= 1
            next_satellite.connection_count -= 1

            # Move to the next satellite
            current_satellite = next_satellite
            path.append(current_satellite)

            if is_final:
                break

        return path

    def train(self, satellites, start_index, end_index, max_iterations=3000):
        self.precompute_matrices(satellites)
        start_satellite = self.satellites[start_index]
        end_satellite = self.satellites[end_index]

        print("Starting Q-Learning Training:")
        for i in range(max_iterations):
            print(f"\t{i+1}/{max_iterations}")
            # Reset connections for all satellites
            for sat in self.satellites:
                sat.connection_count = 0
            # Train for one episode
            optimal_path = self.train_iteration(start_satellite, end_satellite)

        print("Training complete, optimal path:", [sat.index for sat in optimal_path])
        return optimal_path

def test():
    # Example usage:
    num_satellites = 100 # Initialize with 100 satellites
    satellites = [
        Satellite(
            longitude = np.random.uniform(0, 360),
            latitude = np.random.uniform(-90, 90),
            height = 0,
            speed = 0.5
        ) for _ in range(num_satellites)
    ]

    network = Constellation()
    # network.precompute_matrices(satellites)
    optimal_path = network.train(satellites, start_index=0, end_index=87)

if __name__ == '__main__':
    test()