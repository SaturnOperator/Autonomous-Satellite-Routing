import numpy as np

class Satellite:
    EARTH_RADIUS = 6371

    # State Thresholds
    DELAY_LOW = 1000 # Max distance for low LATENCY
    DELAY_MEDIUM = 5000 # Max distance for medium LATENCY, anything above is high
    CONGESTION_LOW = 1 # Max connectsion for low congestion,
    CONGESTION_MEDIUM = 3 # Max connectsion for medium congestion, anything above is high
    CONGESTION_HIGH = 5 # Can't accept connections after this value

    ALPHA = 0.50 # learning rate
    GAMMA = 0.95 # discount factor
    EPSILON = 0.1  # exploration rate
    MAX_ITERATIONS = 1000

    def __init__(self, longitude, latitude, height, speed):
        self.longitude = longitude
        self.latitude = latitude
        self.height = height
        self.speed = speed  # Speed in degrees per update cycle
        self.connections = [] # Number active connections 
        self.Q = {}
    
    def update_position(self): # Moves satellite 1 speed incremenet
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

    def check_latency_state(self, other):
        distance = self.calculate_distance(other)
        if distance <= self.DELAY_LOW:
            return 'low'
        elif distance <= self.DELAY_MEDIUM:
            return 'medium'
        else:
            return 'high'

    def check_congestion(self):
        if len(self.connections) <= self.CONGESTION_LOW:
            return 'low'
        elif len(self.connections) <= self.CONGESTION_MEDIUM:
            return 'medium'
        else:
            return 'high'

    def get_state(self, endpoint_satellite):
        delay_state = self.check_latency_state(endpoint_satellite)
        congestion_state = self.check_congestion()
        return (delay_state, congestion_state)

    def get_possible_actions(self, satellites):
        possible_actions = []
        for sat in satellites:
            if not self.out_of_sight(sat) and sat != self:
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

    def update_q_value(self, state_current, action_current, reward, state_next, satellites):
        # Q(s, a) <- Q(s, a) + \alpha * [r + \gamma * max_a(Q(s_next, a')) - Q(s, a)]
        possible_actions_next = self.get_possible_actions(satellites)
        max_q_next = max([self.Q.get((state_next, a), 0) for a in possible_actions_next], default=0)
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