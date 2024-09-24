import matplotlib.pyplot as plt
import networkz as nx
import numpy as np


def create_random_vector(size: int = 3) -> tuple:
    """
    Generate a random vector of integers that sums to 100, with each element
    being a multiple of 5.

    Parameters:
    size (int): The number of elements in the vector. Default is 3.

    Returns:
    tuple: A tuple containing `size` integers that sum to 100, with each
           element being a multiple of 5.
    """
    vector = np.random.rand(size)
    vector = np.floor(vector / vector.sum() * 20).astype(int)
    # Adjust the last element to ensure the sum is exactly 20
    vector[-1] = 20 - vector[:-1].sum()
    np.random.shuffle(vector)
    # Multiply each value in the vector by 5
    vector = vector * 5
    return tuple(vector)


def sum_of_differences(user_vector: tuple, generated_vector: tuple) -> int:
    """
    Compute the sum of absolute differences between the user-provided vector
    and the generated vector.

    Parameters:
    user_vector (tuple): The user-provided vector.
    generated_vector (tuple): The generated vector.

    Returns:
    int: The sum of absolute differences between the corresponding elements
         of the user vector and the generated vector.

    Example:
    >>> sum_of_differences((10, 20, 30), (15, 25, 35))
    15
    """
    return np.sum(np.abs(np.array(user_vector) - np.array(generated_vector)))


def minimal_ratio(user_vector: tuple, generated_vector: tuple) -> float:
    """
    Compute the minimal ratio between the corresponding elements of the
    user-provided vector and the generated vector.

    Parameters:
    user_vector (tuple): The user-provided vector.
    generated_vector (tuple): The generated vector.

    Returns:
    float: The minimal ratio of the corresponding elements of the generated
           vector to the user vector, ignoring any divisions by zero.

    Example:
    >>> minimal_ratio((50, 30, 20), (30, 40, 30))
    0.6
    """
    ratios = np.array(generated_vector) / np.array(user_vector)
    return np.min(ratios[np.isfinite(ratios)])  # Handle division by zero


def should_add_edge(n1: tuple, s: int, r: float) -> bool:
    """
    Determine whether an edge should be added based on the attributes of the
    given node and the provided sum of differences and minimal ratio.

    Parameters:
    n1 (tuple): A tuple representing the node, where `n1[1]['r']` is the ratio
                and `n1[1]['s']` is the sum of differences.
    s (int): The sum of differences to compare against the node's sum of differences.
    r (float): The minimal ratio to compare against the node's ratio.

    Returns:
    bool: True if an edge should be added, False otherwise.

    Example:
    >>> node = (1, {'r': 0.8, 's': 10})
    >>> should_add_edge(node, 12, 0.9)
    True
    """
    n1r = n1[1]["r"]  # node1 ratio
    n1s = n1[1]["s"]  # node1 diff sum
    if (n1r <= r and n1s <= s) or (n1r >= r and n1s >= s):
        return True
    return False


def get_vector_sr(user_vector: tuple, v: tuple):
    """
    Calculate the sum of differences and the minimal ratio between the user-provided vector
    and another vector.

    Parameters:
    user_vector (tuple): The vector provided by the user.
    v (tuple): The vector to compare against the user vector.

    Returns:
    tuple: A tuple containing two values:
           - The sum of absolute differences between the corresponding elements of the user vector and `v`.
           - The minimal ratio of the corresponding elements of `v` to the user vector, ignoring any divisions by zero.

    Example:
    >>> get_vector_sr((50, 30, 20), (30, 40, 30))
    (40, 0.6)
    """
    return (sum_of_differences(user_vector, v), minimal_ratio(user_vector, v))


def graph_n_edges(user_vector, n: int = 10, vector_size=3) -> nx.Graph:
    """
    Create a graph with up to `n` edges based on the user vector. Edges are added
    only between nodes where one node has both a smaller sum of differences
    and minimal ratio than the other node.

    Parameters:
    user_vector (tuple): The user-provided vector to compare against.
    n (int): The number of edges in the graph. Default is 10.
    vector_size (int): The size of the generated vectors. Default is 3.

    Returns:
    nx.Graph: A NetworkX graph with up to `n` edges.

    Example:
    >>> graph_n_edges((10, 20, 30))
    """
    vectors = set()
    G = nx.Graph()
    while len(G.edges) < n:
        v = create_random_vector(vector_size)
        print(v)
        while v in vectors:
            v = create_random_vector(vector_size)
            print(v)
        vectors.add(v)
        diff_sum, ratio = get_vector_sr(user_vector, v)
        G.add_node(v, s=diff_sum, r=ratio, pos=(diff_sum, ratio))
        for u in G.nodes(data=True):
            if u[0] == v:
                continue
            if should_add_edge(u, diff_sum, ratio):
                G.add_edge(u[0], v)
                if len(G.edges) >= n:
                    break
    return G


def get_user_vector_str(user_vector: tuple) -> str:
    """
    Convert a user-provided vector into a string representation where each element
    is prefixed with a dash ('-').

    Parameters:
    user_vector (tuple): The user-provided vector to convert to a string.

    Returns:
    str: A string representation of the user vector with each element prefixed by a dash.

    Example:
    >>> get_user_vector_str([10, 20, 30])
    '-10-20-30'
    """
    user_vector_str = ""
    for i in user_vector:
        user_vector_str += f"-{i}"
    return user_vector_str


def generate_user_example(
    user_vector: tuple, n=10, vector_size=3, plot=False, save_txt=False
) -> list[tuple[tuple]]:
    """
    Generate a graph based on the user vector and optionally visualize it, save the plot,
    and save the edges to a text file. Returns a list of tuples representing the edges
    of the generated graph.

    Parameters:
    user_vector (tuple): The user-provided vector to use as a basis for the graph.
    n (int): The number of edges in the graph. Default is 10.
    vector_size (int): The size of the generated vectors. Default is 3.
    plot (bool): If True, visualizes the graph and saves the plot as an image file. Default is False.
    save_txt (bool): If True, saves the edges of the graph to a text file. Default is False.

    Returns:
    list[tuple[tuple]]: A list of tuples representing the edges of the generated graph,
                        where each tuple contains two nodes connected by the edge.

    This function creates a graph using the `graph_n_edges` function. If `plot` is True,
    it visualizes the graph using `matplotlib` and saves the resulting plot as a PNG image
    file in the `graphs` folder. If `save_txt` is True, it saves the edges of the graph
    to a text file in the `examples` folder.

    Example:
    >>> generate_user_example((10, 20, 30))
    """
    G = graph_n_edges(user_vector, n, vector_size)
    user_vector_str = get_user_vector_str(user_vector)

    if plot:
        # Draw the graph and save it
        pos = nx.get_node_attributes(G, "pos")
        plt.figure(figsize=(8, 6))
        nx.draw(
            G,
            pos,
            with_labels=True,
            node_color="skyblue",
            node_size=500,
            edge_color="gray",
            font_size=10,
            font_color="black",
        )
        plt.title("Graph Visualization")
        plt.savefig(
            f"examples/graph{user_vector_str}.png"
        )  # Save the plot as an image file

    if save_txt:
        # Save the edges to a text file
        with open(f"examples/example{user_vector_str}.txt", "w") as file:
            for e in G.edges:
                file.write(f"{e[0]} {e[1]}\n")

    return list(G.edges)
