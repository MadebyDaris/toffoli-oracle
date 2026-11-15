from toffoli_oracle import Xag

x = Xag()
a, b, c = x.add_input("a"), x.add_input("b"), x.add_input("c")

x.add_output(x.add_and(x.add_and(a, b), c), "f")  # f = (a AND b) AND c
print(bin(x.simulate()[0]), "ANDs:", x.num_ands, "AND-depth:", x.and_depth())
