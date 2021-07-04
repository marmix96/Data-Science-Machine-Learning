#askisi_2a
set.seed(03400100)

f     = function(x) {return (exp(x) / (exp(3) - 1) )}
F_inv = function(x) {return (log(1 + x*(exp(3) - 1)))}


u = runif(1000)
x = F_inv(u)

hist(x, prob = T, xlab='X', ylim = c(0, 1.2), xlim = c(0, 3), main='Inversion Sampling')
curve(f , from = 0, to = 3, lwd=2, xlab = "", ylab = "", add = T, col = "red", yaxt = "n")


#askisi_2b
set.seed(03400100)

accepted_counter = 0
total_samples = 0
accepted_samples = c()
N = 1000
M = 3 * exp(3) / (exp(3) - 1)
my_unif = function(x) {return (M * dunif(x, min = 0, max = 3))}


while (accepted_counter < N) {
  y = runif(1, min = 0, max = 3)
  u = runif(1)
  if (u <= f(y) / (M*dunif(y, min=0, max=3))) {
    accepted_counter = accepted_counter + 1
    accepted_samples = c(accepted_samples, y)
  }
  total_samples = total_samples + 1
}

print(paste("Total samples needed: ", total_samples))
print(paste("Theoretical acceptance probability = ", signif(1/M, 5), "Estimated acceptance probability = ", signif(accepted_counter / total_samples, 5)))
hist(accepted_samples, prob = T, xlab='X', ylim = c(0, 1.2), xlim = c(0, 3), main='Rejection Sampling')
plot(f , from = 0, to = 3, lwd=2, xlab = "", ylab = "", add = T, col = "red", yaxt = "n")
curve(my_unif , from = 0, to = 3, lwd=2, xlab = "", ylab = "", add = T, col = "green", yaxt = "n")

#askisi_2c
set.seed(50)
Epanechnikov = function(x_i, x_j, h) { return (pmax(0.75 * (1 - ((x_i - x_j) / h)^2), 0))}

likelihood_CLV = function(s, h) {
  L = 1
  for (i in 1:length(s)) L = L * mean(Epanechnikov(s[i], s[-i], h)) / h
  return (L)
}

L_opt = -Inf
h_opt = NA
samples = F_inv(runif(100))

for (h in seq(0.01, 3, 0.01)) {
  L = likelihood_CLV(samples, h)
  if (L > L_opt) {
    L_opt = L
    h_opt = h
  }
}    

print(paste("h_opt = ", h_opt))

f_hat = function(x) return (mean(Epanechnikov(x, samples, h_opt)) / h_opt)

X = seq(0, 3, 0.001)
Y = lapply(X, f_hat)
plot(X, Y, 'l', xlim = c(0, 3), ylim = c(0,1.1), col='green', main = "Kernel Density Estimation")
curve(f, 0, 3, add=T, col='red')

#askisi_2d
set.seed(17)

B = 1000
n = 10
samples = F_inv(runif(n))

T_test = abs(2 - mean(samples))
samples_move = samples + 2 - mean(samples)

bootstrap_ask_2d = function(B, n, s) {
  boot = c()
  for(i in 1:B){
    sam = sample(s, n, replace=TRUE)
    J = mean(sam)
    boot = c(boot, J)
  }
  return (boot)
}

p_value  = (sum(abs(2 - bootstrap_ask_2d(B, n, samples_move)) > T_test) + 1) / (B + 1)
print(paste("p_value = ", p_value))

samples_boot = bootstrap_ask_2d(B, n, samples)
Confidence_Interval = sort(samples_boot)[25:975]
print(paste("Confidence Interval 95% = (", Confidence_Interval[1], ",", Confidence_Interval[951], ")"))