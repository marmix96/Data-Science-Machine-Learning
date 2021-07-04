set.seed(17)
a  = 2
b  = 5
n  = 10000
xi = rpois(n, rgamma(n, shape=a, rate=b))
xmean = mean(xi)

EM = function(a0, b0) {
  a_old = a0
  b_old = b0
  em_counter = 0
  repeat {
    repeat {
      arithmhths = + n*log(a_old / (xmean + a_old)) - n*digamma(a_old)  + sum(sapply((xi + a_old), digamma))
      paronomasths = -n*trigamma(a_old) + n/a_old
      a_new = a_old - arithmhths/paronomasths
      if ((a_new - a_old)^2 <= 10^(-10)) break
      a_old = a_new
    }
    b_new = a_new * (1 + b_old) / (xmean + a_old)
    if ((a_new - a_old)^2 + (b_new - b_old)^2 <= 10^(-10)) break
    a_old = a_new
    b_old = b_new
    em_counter = em_counter + 1 
  }
  return (c(a_new, b_new, em_counter))
}
EM(1, 1)