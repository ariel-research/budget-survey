# https://equalshares.net/implementation/computation/
import copy
import logging
import time
import matplotlib.pyplot as plt

logger = logging.getLogger("equal_shares_logger")



"""
 The purpose of min_max_equal_shares function is to convert the input in the received format
 to a format suitable for the equal_shares function (Selects the minimum value)



   Args:
        voters (list): A list of voter names.
        projects (list): A list of project IDs.
        cost_min_max (dict): A dictionary mapping project IDs to their min and max costs.
        bids (dict): A dictionary mapping project IDs to the list of voters who approve them and the cost the voters chose.
        budget (int): The total budget available
        budget_increment_per_project (int) : A const number marking the steps between the maximum and minimum price

 example:
        cost_min_max = [{1: (200, 700)}, {2: (300, 900)}, {3:(100,100)}] --> cost = [{1:200 }, {2:300}, {3:100}]


"""


def min_max_equal_shares(voters:list, projects: list, cost_min_max: dict, bids: dict, budget: int, budget_increment_per_project: int):

    """


    # T.0
    # >>> voters = [1, 2, 3, 4, 5]  # Voters
    # >>> projects = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]  # Project IDs
    # >>> cost = [{1: (100, 200)}, {2: (150, 250)}, {3: (200, 300)}, {4: (250, 350)}, {5: (300, 400)},{6: (350, 450)}, {7: (400, 500)}, {8: (450, 550)}, {9: (500, 600)}, {10: (550, 650)}]
    # >>> bids = { 1: {1: 100, 2: 130, 4: 150},2: {2: 160, 5: 190},3: {1: 200, 5: 240}, 4: {3: 270, 4: 280, },5: {2: 310, 3: 320, 5: 340},6: {2: 360, 5: 390}, 7: {1: 400, 4: 430, },8: {2: 460, 5: 490},9: {1: 500, 3: 520,  5: 540},10:{2: 560, 3: 570, }}
    # >>> budget = 900  # Total budget
    # >>> budget_increment_per_project = 10
    # >>> min_max_equal_shares(voters, projects, cost, bids, budget,budget_increment_per_project)
    ([1, 3, 4, 5], {1: 130, 2: 0, 3: 200, 4: 250, 5: 320, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0})
    #
    # T.1
    # >>> voters = [1, 2]  # voter
    # >>> projects = [1, 2, 3]  # Project IDs
    # >>> cost_min_max = [{1: (200, 700)}, {2: (300, 900)}, {3:(100,100)}]
    # >>> bids = {1: {1: 500, 2:200}, 2: {1: 300, 2: 300} ,3:{2:100}}
    # >>> budget = 900  # Budget
    # >>> budget_increment_per_project = 10
    # >>> min_max_equal_shares(voters, projects, cost_min_max, bids, budget, budget_increment_per_project)
    # ([1, 2, 3], {1: 500, 2: 300, 3: 100})
    #
    # # T.2
    # >>> voters = [1, 2]  # voter
    # >>> projects = [1, 2]  # Project IDs
    # >>> cost_min_max = [{1: (99, 200)}, {2: (98, 200)}]
    # >>> bids = {1: {2:99}, 2: {1:98}}
    # >>> budget = 100  # Budget
    # >>> budget_increment_per_project = 10
    # >>> min_max_equal_shares(voters, projects, cost_min_max, bids, budget, budget_increment_per_project)
    # ([2], {1: 0, 2: 98})
    #
    # # T.3
    # >>> voters = [1, 2, 3, 4]  # voter
    # >>> projects = [1, 2, 3, 4]  # Project IDs
    # >>> cost = [{1: (500, 600)}, {2: (500, 600)}, {3: (500, 600)}, {4: (500, 600)}]
    # >>> bids = {1: {1: 500, 2: 500 ,3: 500, 4: 500 }, 2: {1: 500, 2: 500 ,3: 500, 4: 500 }, 3: {1: 500, 2: 500 ,3: 500, 4: 500 }, 4: {1: 500, 2: 500 ,3: 500, 4: 500 }}  # for each project
    # >>> budget = 500  # Total budget
    # >>> budget_increment_per_project = 10
    # >>> min_max_equal_shares(voters, projects, cost, bids, budget, budget_increment_per_project)
    # ([1], {1: 500, 2: 0, 3: 0, 4: 0})
    #
    # #  T.4
    #
    # # For one projects with one voter.
    # >>> voters = [1]  # voter
    # >>> projects = [1]  # Project IDs
    # >>> cost = [{1: (500, 600)}]  # Cost for each project
    # >>> bids = {1: {1: 600}}  # Approvers for each project
    # >>> budget = 1000  # Budget
    # >>> budget_increment_per_project = 10
    # >>> min_max_equal_shares(voters, projects, cost, bids, budget,budget_increment_per_project)
    # ([1], {1: 600})
    #
    # # T.5
    #
    # >>> voters = [1, 2, 3]  # voter
    # >>> projects = [1, 2 ,3 ]  # Project IDs
    # >>> cost = [{1: (500, 600)}, {2:  (500, 600)}, {3:  (500, 600)}]
    # >>> bids = {1: {1: 500, 2: 500, 3: 500}, 2: {1: 500, 2: 500, 3: 500} , 3: {1: 500, 2: 500, 3: 500}}   #  for each project
    # >>> budget = 1500                 # Total budget
    # >>> budget_increment_per_project = 10
    # >>> min_max_equal_shares(voters, projects,cost,bids,budget,budget_increment_per_project)
    # ([1, 2, 3], {1: 500, 2: 500, 3: 500})

    """

    cost = {}
    for item in cost_min_max:
        project_id, (min_value, _) = item.popitem()
        cost[project_id] = min_value

    approvers = {}
    for project_id, value in bids.items():
        approvers[project_id] = list(value.keys())

    return equal_shares(voters, projects, cost, approvers, budget, bids, budget_increment_per_project)


def equal_shares(voters: list, projects: list, cost: dict, approvers: dict, budget: int, bids: dict, budget_increment_per_project: int):

    max_cost_for_project = find_max(bids)
    chosen_project, chosen_project_cost, update_cost,budget_per_voter = equal_shares_fixed_budget(voters, projects, cost, approvers, budget, bids, budget_increment_per_project,max_cost_for_project)

    # add 1 completion
    # start with integral per-voter voters_budget
    voters_budget = int(budget / len(voters)) * len(voters)
    total_chosen_project_cost = sum(chosen_project_cost[c] for c in chosen_project_cost)

    while True:
        # is current outcome exhaustive?
        is_exhaustive = True
        for project in projects:
            max_value_project = max_cost_for_project[project]
            project_cost = update_cost[project]



            # chack if total cost of chosen project + current project  <= budget, if true have more project to chack
            # check if total cost of chosen project + project_cost   <= budget
            # and total project_cost + curr project_cost <= max value for curr project, if true thr price of the project can be increased

            if (project not in chosen_project and total_chosen_project_cost + cost[project] <= budget) or \
                    (project in chosen_project and total_chosen_project_cost + project_cost <= budget and
                     chosen_project_cost[project] + project_cost <= max_value_project):
                is_exhaustive = False

                break
        # if so, stop
        if is_exhaustive:
            break
        # would the next highest voters_budget work?
        update_voters_budget = voters_budget + len(voters)  # Add 1 to each voter's voters_budget
        logger.info("  call fix voters_budget   = %s B= %s, %s", total_chosen_project_cost, budget, update_voters_budget)
        update_chosen_project, update_chosen_project_cost, update_cost, update_budget_per_voter = equal_shares_fixed_budget(voters, projects, cost, approvers, update_voters_budget, bids, budget_increment_per_project,max_cost_for_project)
        total_chosen_project_cost = sum(update_chosen_project_cost[c] for c in update_chosen_project_cost)

        if total_chosen_project_cost <= budget:
            # yes, so continue with that voters_budget
            voters_budget = update_voters_budget
            chosen_project = update_chosen_project
            chosen_project_cost = update_chosen_project_cost
            budget_per_voter = update_budget_per_voter
        else:
            # logger.info("  break total_chosen_project_cost  = %s B= %s", total_chosen_project_cost, B)
            # no, so stop
            break
    plot_graph(chosen_project_cost)

    return chosen_project, chosen_project_cost,budget_per_voter


def break_ties(cost: dict, approvers: dict, bids: list):
    remaining = bids.copy()
    best_cost = min(cost[c] for c in remaining)  # first the min cost project
    remaining = [c for c in remaining if cost[c] == best_cost]
    best_count = max(len(approvers[c]) for c in remaining)  # second the max voter for project
    remaining = [c for c in remaining if len(approvers[c]) == best_count]
    remaining = [min(remaining)]  # Ensure there is only one remaining project, third the min index project
    return remaining


def equal_shares_fixed_budget(voters: list, projects: list, cost: dict, approvers: dict, budget: int, bids: dict, budget_increment_per_project:int,max_cost_for_project:dict):

    # logger.info("Equal shares with fixed voters_budget: voters=%s, candidates=%s, cost=%s, approvers=%s, voters_budget=%s", N, C,
    #             cost, approvers, B)
    voters_budget = {i: budget / len(voters) for i in voters}

    remaining = {}  # remaining candidate -> previous effective vote count

    budget_per_voter = {}
    for outer_key, inner_dict in bids.items():
        # Initialize the inner dictionary with values set to 0
        budget_per_voter[outer_key] = {inner_key: 0 for inner_key in inner_dict.keys()}

    for c in projects:
        if cost[c] > 0 and len(approvers[c]) > 0:
            remaining[c] = len(approvers[c])

    # logger.info("Remaining --> the number of relevant vote for any project remaining=%s", remaining)

    winners = []

    update_bids = copy.deepcopy(bids)
    update_approvers = copy.deepcopy(approvers)
    update_cost = copy.deepcopy(cost)
    winners_total_cost = {key: 0 for key in projects}

    while True:

        best = []
        best_eff_vote_count = 0

        # go through remaining candidates in order of decreasing previous effective vote count
        remaining_sorted = sorted(remaining, key=lambda c: remaining[c], reverse=True)

        for c in remaining_sorted:
            previous_eff_vote_count = remaining[c]
            if previous_eff_vote_count < best_eff_vote_count:
                # c cannot be better than the best so far
                # logger.info("c cannot be better than the best so far c=%s", c)

                break
            money_behind_now = sum(voters_budget[i] for i in update_approvers[c])
            if money_behind_now < update_cost[c]:
                # c is not affordable
                del remaining[c]
                # logger.info("c is not affordable c=%s, update_cost for c=%s ", update_cost[c])
                continue
            # calculate the effective vote count of c
            update_approvers[c].sort(key=lambda i: voters_budget[i])
            paid_so_far = 0
            denominator = len(update_approvers[c])
            for i in update_approvers[c]:
                # compute payment if remaining approvers pay equally
                max_payment = (update_cost[c] - paid_so_far) / denominator
                eff_vote_count = update_cost[c] / max_payment
                if max_payment > voters_budget[i]:
                    # i cannot afford the payment, so pays entire remaining voters_budget
                    paid_so_far += voters_budget[i]
                    denominator -= 1
                else:
                    # i (and all later approvers) can afford the payment; stop here
                    remaining[c] = int(eff_vote_count)
                    if eff_vote_count > best_eff_vote_count:
                        best_eff_vote_count = eff_vote_count
                        best = [c]
                    elif eff_vote_count == best_eff_vote_count:
                        best.append(c)

                    break
        if not best:
            # logger.info(" no remaining candidates are affordable ,best = %s", best)

            break
        best = break_ties(update_cost, update_approvers, best)
        # logger.info(" after vreak ties ,best  = %s", best)

        if len(best) > 1:
            raise Exception(f"Tie-breaking failed: tie between projects {best} " + \
                            "could not be resolved. Another tie-breaking needs to be added.")
        best = best[0]
        winners.append(best)
        winners = set(winners)
        winners = list(winners)

        logger.info("  ,winners  = %s", winners)



        """

            After receiving the selected project, we reduce the cost of the selected project from the Update_bids list
            and create a new project with a "factor" cost, we filter its data using the
            filter_bids function.Then they check whether the total price of the project does not exceed the highest price they chose.
            and update "remaining" with the number of voters who chose it at the new price. and continue the while loop.

        """

        # the project curr id number and  cost

        curr_project_id = best
        curr_project_cost = update_cost[best]

        logger.info(" id and cost for the chosen project   = %s, %s", curr_project_id, curr_project_cost)

        # Find the highest choice for the current project
        max_value_project = max_cost_for_project[curr_project_id]
        # Deducts from the voters_budget of each voter who chose the current project the relative part for the current project

        best_max_payment = curr_project_cost / best_eff_vote_count


        for i in update_bids[curr_project_id].keys():
            if voters_budget[i] > best_max_payment:
                voters_budget[i] -= best_max_payment
                budget_per_voter[curr_project_id][i] = budget_per_voter[curr_project_id][i] + best_max_payment
            else:
                voters_budget[i] = 0

        # chack if the curr cost + total update codt <= max value for this projec
        # logger.info(" total project price   = %s", winners_total_cost[curr_project_id])

        if winners_total_cost[curr_project_id] + curr_project_cost <= max_value_project:

            filter_bids(update_bids, update_approvers, curr_project_id, curr_project_cost, budget_increment_per_project, update_cost)

            winners_total_cost[curr_project_id] = winners_total_cost[curr_project_id] + curr_project_cost

            # Updates the remaining list in the number of voters after updating the price of the project
            remaining[curr_project_id] = len(update_bids[curr_project_id].keys())


            # logger.info(" update cost= %s", update_cost)
            # logger.info(" update bids= %s", update_bids)
            # logger.info(" update approvers= %s", update_approvers)

        else:

            update_cost[curr_project_id] = 0
            del remaining[curr_project_id]

    # logger.info("  ,winners return  = %s", winners)
    return winners, winners_total_cost, update_cost,budget_per_voter




# return list - the  max voter price for any project
def find_max(bids: dict):
    max_result = {key: 0 for key in bids}

    for project_id in bids:
            max_result[project_id] = max(bids[project_id].values() , default=0)  # Find the maximum value in the list

    return max_result


def filter_bids(bids: dict, approvers: dict, project_id: int, project_cost: int, budget_increment_per_project: int, cost: dict):
    if project_id in bids:
        voters_to_remove = []
        for voter_id, price in bids[project_id].items():
            update_project_price = price - (project_cost + budget_increment_per_project)  # for the next iteration
            if update_project_price < 0:
                voters_to_remove.append(voter_id)
                cost[project_id] = budget_increment_per_project
            else:
                bids[project_id][voter_id] = update_project_price + budget_increment_per_project
                cost[project_id] = budget_increment_per_project

        for voter_id in voters_to_remove:
            bids[project_id].pop(voter_id)

    approvers[project_id] = list(bids[project_id].keys())

def plot_graph(data):
    plt.figure(figsize=(8, 6))
    plt.bar(data.keys(), data.values(), color='skyblue')
    plt.xlabel('Project ID')
    plt.ylabel('Price')
    plt.title('Price Distribution for Projects')
    plt.xticks(list(data.keys()))  # Set X-axis ticks to match the keys of the input data
    plt.show()



if __name__ == "__main__":
    import doctest, sys
    print(doctest.testmod())

    sys.exit(1)

    logger.setLevel(logging.WARNING)  # Turn off "info" log messages
    logger.setLevel(logging.INFO)  # Turn on "info" log messages
    logger.addHandler(logging.StreamHandler())
    # T.0 Testing of multiple projects
    N = [1, 2, 3, 4, 5]  # Voters
    C = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]  # Project IDs
    cost = [
        {1: (100, 200)}, {2: (150, 250)}, {3: (200, 300)}, {4: (250, 350)}, {5: (300, 400)},
        {6: (350, 450)}, {7: (400, 500)}, {8: (450, 550)}, {9: (500, 600)}, {10: (550, 650)}
    ]
    bids = {
        1: {1: 100, 2: 130, 4: 150},
        2: {2: 160, 5: 190},
        3: {1: 200, 5: 240},
        4: {3: 270, 4: 280, },
        5: {2: 310, 3: 320, 5: 340},
        6: {2: 360, 5: 390},
        7: {1: 400, 4: 430, },
        8: {2: 460, 5: 490},
        9: {1: 500, 3: 520,  5: 540},
        10:{2: 560, 3: 570, }
    }
    B = 1000  # Total budget
    factor = 10
    start_time = time.time()
    # Call the function
    print(" T.0 result: ", min_max_equal_shares(N, C, cost, bids, B,factor))
    # Record the end time
    end_time = time.time()
    # Calculate the elapsed time
    elapsed_time = end_time - start_time
    print(f"Function executed in {elapsed_time:.4f} seconds")


    #
    # # T.1 Three projects with different prices
    # N = [1, 2]  # voter
    # C = [1, 2, 3]  # Project IDs
    # cost_min_max = [{1: (200, 700)}, {2: (300, 900)}, {3:(100,100)}]
    # bids = {1: {1: 500, 2:200}, 2: {1: 300, 2: 300} ,3:{2:100}}
    # B = 900  # Budget
    # factor = 100
    # start_time = time.time()
    # print(" T.1 result: ", min_max_equal_shares(N, C, cost_min_max, bids, B,factor))
    # # Record the end time
    # end_time = time.time()
    # # Calculate the elapsed time
    # elapsed_time = end_time - start_time
    # print(f"Function executed in {elapsed_time:.4f} seconds")

    # # T.2 Two projects with the same amount of voters and the price difference between them is 1
    # N = [1, 2]  # voter
    # C = [1, 2]  # Project IDs
    # cost_min_max = [{1: (99, 200)}, {2: (98, 200)}]
    # bids = {1: {2:99}, 2: {1:98}}
    # B = 100  # Budget
    # factor = 10
    # print(" T.2 result: ", min_max_equal_shares(N, C, cost_min_max, bids, B, factor))

    ## T.3 For 4 projects with same cost and same voters, while the budget suffices for all the 1 ( take the first index) .
    # N = N = [1, 2, 3, 4]  # voter
    # C = [1, 2, 3, 4]  # Project IDs
    # cost = [{1: (500, 600)}, {2: (500, 600)}, {3: (500, 600)}, {4: (500, 600)}]
    # bids = {1: {1: 500, 2: 500 ,3: 500, 4: 500 }, 2: {1: 500, 2: 500 ,3: 500, 4: 500 }, 3: {1: 500, 2: 500 ,3: 500, 4: 500 }, 4: {1: 500, 2: 500 ,3: 500, 4: 500 }}  # for each project
    # B = 500  # Total budget
    # factor = 10
    # print( " T.3 result: ",min_max_equal_shares(N, C, cost, bids, B,factor))

    # # T.4 For one projects with one voter. the budget > project cost.
    # N = [1]  # voter
    # C = [1]  # Project IDs
    # cost = [{1: (500, 600)}]  # Cost for each project
    # bids = {1: {1: 600}}  # Approvers for each project
    # B = 1000  # Budget
    # factor = 10
    # print( " T.4 result: ",min_max_equal_shares(N, C, cost, bids, B,factor))

    # T.5 For one projects with one voter. the budget <= project min cost.
    # N = [1]  # voter
    # C = [1]  # Project IDs
    # cost = [{1: (500, 600)}]  # Cost for each project
    # bids = {1: {1: 600}}  # Approvers for each project
    # B = 500  # Budget
    # factor = 10
    # print( " T.5 result: ",min_max_equal_shares(N, C, cost, bids, B,factor))
    #
    # # T.6 For one projects with one voter. the budget < project min  cost.
    # N = [1]  # voter
    # C = [1]  # Project IDs
    # cost = [{1: (600, 600)}]  # Cost for each project
    # bids = {1: {1: 600}}  # Approvers for each project
    # B = 500  # Budget
    # factor = 10
    # print( " T.6 result: ",min_max_equal_shares(N, C, cost, bids, B,factor))
    #
    # # T.7  For 3 projects with same cost and same voters, while the budget suffices for all the 3 .
    # N = [1, 2, 3]  # voter
    # C = [1, 2 ,3 ]  # Project IDs
    # cost = [{1: (500, 600)}, {2:  (500, 600)}, {3:  (500, 600)}]
    # bids = {1: {1: 500, 2: 500, 3: 500}, 2: {1: 500, 2: 500, 3: 500} , 3: {1: 500, 2: 500, 3: 500}}   #  for each project
    # B = 1500                 # Total budget
    # factor = 10
    # print( " T.7 result: ",min_max_equal_shares(N, C,cost,bids,B,factor))
    # #
