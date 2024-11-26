import numpy as np
from multiprocessing import Queue

from satellite import Satellite

class Constellation:
    MAX_ITERATIONS = 3000
    iteration_count = 0

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
        max_steps = 10000
        step = 0
        while current_satellite != end_satellite:
            if step > max_steps:
                print(f"Max steps exceeded in iteration.")
                break

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
            # current_satellite.num_connections += 1
            # next_satellite.num_connections += 1

            is_final = next_satellite == end_satellite
            state_next = next_satellite.get_state(end_satellite.index)
            reward = current_satellite.get_reward(state_next, is_final)

            current_satellite.update_q_value(
                state_current, action_current, reward, state_next
            )

            # Simulate removing the connection (decreasing congestion)
            # current_satellite.num_connections -= 1
            # next_satellite.num_connections -= 1

            # Move to the next satellite
            current_satellite = next_satellite
            path.append(current_satellite)

            step +=1

            if is_final:
                break
        return path

    def train(self, satellites, start_index, end_index):
        self.precompute_matrices(satellites)
        start_satellite = self.satellites[start_index]
        end_satellite = self.satellites[end_index]

        print("Starting Q-Learning Training:")
        for i in range(self.MAX_ITERATIONS):
            print(f"\t{i+1}/{self.MAX_ITERATIONS}")
            self.iteration_count = i+1
            # Reset connections for all satellites
            # for sat in self.satellites:
            #     sat.num_connections = 0
            
            # Train for one episode
            optimal_path = self.train_iteration(start_satellite, end_satellite)

        print("Training complete, optimal path:", [sat.index for sat in optimal_path])
        return optimal_path

    def train_wrapper(self, satellites, start_index, end_index, results):
        try:
            optimal_path = self.train(satellites, start_index, end_index)
            results.put(optimal_path)
        except Exception as e:
            if e.errno == errno.EPIPE: 
                pass
            else:
                print("error", str(e))

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
    optimal_path = network.train(satellites, start_index=0, end_index=87)

if __name__ == '__main__':
    test()