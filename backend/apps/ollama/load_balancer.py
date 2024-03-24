from abc import ABC


class LoadBalancer:
    def __init__(self, strategy=None):
        self.models_map = None  # List to store server details
        if strategy is None:
            strategy = RoundRobinStrategy()
        self.strategy = strategy  # Load balancing strategy

    def set_model_map(self, models_map):
        self.models_map = models_map

    def get_server_idx_for_model(self, model: str):
        """
        Get a server idx to handle requests for the given model using the specified strategy.
        """
        selected_server = self.strategy.select_server(self.models_map, model)
        print(f"selected_server: {selected_server}")
        return selected_server


class LoadBalancingStrategy(ABC):
    def select_server(self, models_map, model):
        raise NotImplementedError


class RoundRobinStrategy(LoadBalancingStrategy):
    def __init__(self):
        self.current_index = 0

    def select_server(self, models_map, model: str):
        servers_supporting_model = list(set(models_map.get(model, {})["urls"]))

        if not servers_supporting_model:
            return None  # No server supports the requested model

        selected_server = servers_supporting_model[
            self.current_index % len(servers_supporting_model)
        ]
        self.current_index += 1
        return selected_server


class WeightedRoundRobinStrategy(LoadBalancingStrategy):
    def __init__(self):
        self.weights = {}
        self.current_index = 0

    def set_weights(self, weights):
        self.weights = weights
        print(f"weights: {weights}")

    def select_server(self, models_map, model: str):
        servers_supporting_model = list(set(models_map.get(model, {})["urls"]))

        if not servers_supporting_model:
            return None  # No server supports the requested model

        total_weight = sum(self.weights)
        selected_index = self.current_index % total_weight
        server_weights = {
            server: self.weights[server] for server in servers_supporting_model
        }

        self.current_index += 1

        for server_idx, weight in server_weights.items():
            if selected_index < weight:
                return server_idx
            selected_index -= weight

        # print("Falling back to first server")
        return servers_supporting_model[0]  # Fallback to the first server
