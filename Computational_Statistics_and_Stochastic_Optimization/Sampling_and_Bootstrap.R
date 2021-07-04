#askisi 1a
set.seed(03400100)
Monte_Carlo = function(n, a) {
  return (mean((rnorm(n) + a)^2))
  }

for (a in 0:4)
  for (n in c(100,1000))
    print(paste("for n = ", n, "and a = ", a, "MC estimation is", signif(Monte_Carlo(n,a), 5)))

#askisi 1c
set.seed(03400100)
Importance_Sampling = function(n, a) {
  samples = rnorm(n, mean = a)
  return (mean((samples + a)^2 * dnorm(samples) / dnorm(samples-a)))
}

for (a in 0:4)
  for (n in c(100,1000))
    print(paste("for n = ", n, "and a = ", a, "IS estimation is", signif(Importance_Sampling(n,a),5)))

for(a in 0:4){
  for (n in c(100, 1000)){
  sdmc <- sqrt((4*a^2 + 2) / n)
  sdimp <- sqrt((3*exp(a^2) - 1 - 2*(a^2) - a^4) / n)
  print(paste("for n = ", n, "and a = ", a, "MC =", signif(sdmc, 5), "IM =", signif(sdimp, 5)))
  }
}

#askisi_1d
set.seed(03400100)
a = 4
n = 1000
B = 200

original_samples = sample(rnorm(n), n, replace=TRUE)

bootstrap_ask_1d = function(B, n, a) {
  boot = c()
  for(i in 1:B){
    bootstrap_samples = sample(original_samples, n, replace=TRUE)
    J = 1/n*(sum((bootstrap_samples + a) ^ 2))
    boot = c(boot, J)
  }
  std = sd(boot)
  return (std)
}

print(paste("Standard Deviation of Estimator: ", signif(bootstrap_ask_1d(B, n, a), 5)))
print(paste("Theoretical SD of Estimator: ", signif(sqrt((4 * a ^ 2 + 2) / 1000), 5)))

