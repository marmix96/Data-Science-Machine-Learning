#import libraries for data pre-processing
library("data.table")
suppressMessages(library("lubridate"))
library("dplyr")


#step 0 (reading)
conf <- fread('https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv')
dead <- fread('https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv')

#step 1
df_conf <- conf[, -c("Province/State", "Lat", "Long")]
df_dead <- dead[, -c("Province/State", "Lat", "Long")]

#step 2, 4
df_long_conf <- melt(df_conf, id.vars = "Country/Region", variable.name = "date", value.name = "confirmed")
df_long_dead <- melt(df_dead, id.vars = "Country/Region", variable.name = "date", value.name = "deaths")
df_long_conf = data.table(df_long_conf)
df_long_dead = data.table(df_long_dead)

#step 3
#names(df_long_conf)[1] <- "Country"

setnames(df_long_conf, "Country/Region", "Country")
setnames(df_long_dead, "Country/Region", "Country")


#step 5
df_long_conf$date = mdy(df_long_conf$date)
df_long_dead$date = mdy(df_long_dead$date)

# Bonus Part
# replace countries with multiple entries (= more than one Province/State originally)
# with their respective sum
df_long_conf = df_long_conf[, .(confirmed = sum(confirmed)), by = .(Country, date)]
df_long_dead = df_long_dead[, .(deaths    = sum(deaths))   , by = .(Country, date)]

#step 6
df_long_conf <- df_long_conf[, confirmed, by = .(Country, date)]
df_long_dead <- df_long_dead[, deaths   , by = .(Country, date)]

#step 7
#df_long_merged <- cbind(df_long_conf, deaths = df_long_dead$deaths)
df_long_merged <- merge(df_long_conf, df_long_dead)

#step 8
# last_date = df_long_merged[, .SD[which.max(date)], by = Country]
# total_cases = sum(last_date[, "confirmed"])
# total_deaths = sum(last_date[, "deaths"])

# colSums(df_long_merged[, .SD[which.max(date)], by = Country ][,c("confirmed", "deaths")])

#total_per_day <- df_long_merged[, lapply(.SD, sum), by = date, .SDcols = c('confirmed','deaths')]
#sprintf("Worlds latest update: confirmed: %d deaths: %d", tail(total_per_day, 1)$confirmed, tail(total_per_day, 1)$deaths)

colSums(df_long_merged[which(date == max(date))][, c("confirmed", "deaths")])
  
#step 9
df_long_merged <- df_long_merged[order(Country, date)]

#step 10

# df_long_merged$confirmed.ind <- df_long_merged$confirmed - lag(df_long_merged$confirmed, n=1)
# df_long_merged$deaths.inc <- df_long_merged$deaths - lag(df_long_merged$deaths, n=1)

# starting_date <- "2020-01-22"
# df_long_merged[date == starting_date]$confirmed.ind <- 0
# df_long_merged[date == starting_date]$deaths.inc <- 0

# df_long_merged %>% group_by(Country) %>% mutate(confirmed.ind = c(confirmed[1], (confirmed - lag(confirmed, n=1))[-1]), deaths.inc = c(deaths[1], (deaths - lag(deaths))[-1]))
df_long_merged <- df_long_merged[, c("confirmed.ind", "deaths.inc") := lapply(.SD, function(x){x - shift(x, fill = 0)}), by = Country, .SDcols = c("confirmed", "deaths")]


#import libraries for exploratory data analysis
library(ggplot2)
library(scales)
library(ggrepel)
library(ggpubr)
library(grid)
library(cowplot)

#import seasons to our dataset
df_long_merged$month <- month(df_long_merged$date) 

df_long_merged <- df_long_merged[month %in% c(1, 2 ,12), Season := "Winter"]
df_long_merged <- df_long_merged[month %in% c(3, 4 ,5), Season := "Spring"]
df_long_merged <- df_long_merged[month %in% c(6, 7 ,8), Season := "Summer"]
df_long_merged <- df_long_merged[month %in% c(9, 10 ,11), Season := "Fall"]

#select Greece
Greece = df_long_merged[Country=="Greece"][which(confirmed > 0)]

# ggplot(Greece, aes(x = date, y = confirmed.ind)) + 
  # geom_bar(stat = "identity") +
  # theme_bw() +
  # labs(x = "Month", y = "Cumulative Confirmed cases")

p1_data = ggplot(Greece, aes(x = date)) + 
  geom_line(aes(y = confirmed), color = "blue") +
  geom_line(aes(y = deaths)   , color = "red")

p1_data +
  labs(title = "Cumulative confirmed cases and deaths in Greece in logarithmic scale", x = "Month", y = "Confirmed COVID-19 cases and deaths in  Greece") +
  scale_x_date(labels = date_format("%d-%b-%y"), date_breaks = "1 month") +
  scale_y_continuous(labels=comma) + #breaks = Greece[day(date) == 01,confirmed]) +
  theme(axis.text.x = element_text(angle = 90, vjust = 0.5, hjust=1),
        axis.title.y = element_text(margin = margin(r = 20)),
        axis.title.x = element_text(margin = margin(t=20))) +
  scale_y_log10()

#day with most confirmed cases  in Greece
temp <- head(Greece[order(-confirmed.ind, -deaths.inc)], n = 1)

p2a <- ggplot(Greece, aes(x = date)) +
  geom_bar(aes(y = confirmed.ind), stat="identity", color = "blue") +
  geom_bar(aes(y = deaths.inc), stat="identity", color = "red") 
  
  #geom_label(aes(label = temp[,date], y = temp[, confirmed.ind]))

  
p2a <- p2a +
  annotate("text", x = temp$date, y=temp$confirmed.ind, label = temp$date) +
  labs(title = "Daily confirmed cases and deaths in Greece", x = "month", y = "Daily cases and deaths in Greece" )

#select Greece per week and check how year 2020 ended 
Gr_weeks <- Greece[, .(conf_weekly = sum(confirmed.ind), death_weekly = sum(deaths.inc)), by = .(week = paste0(week(date), "_", year(date)))]
Gr_weeks.m <- melt(Gr_weeks[week %in% paste0((c(40:52)), "_2020")], id.var = "week")

p2b <- ggplot(Gr_weeks.m, aes(x=week, y=value, fill = variable)) +
  geom_bar(stat = "identity", position = 'stack') + 
  theme(axis.text.x = element_text(angle = 90, vjust = 0.5, hjust = 1)) +
  scale_fill_manual("legend", values = c("conf_weekly" = "black", "death_weekly" = "orange")) +
  labs(title = "Last weeks for 2020 in Greece", y = "weekly cases and deaths in Greece")


ggarrange(p2a, p2b)


#geom_text_repel(data = temp, aes(label=date)))

#r_weeks <- Greece[, .(conf_week = sum(confirmed.ind)), by = week(date)] 

#select Greece by month
select = c("confirmed.ind", "deaths.inc")
rename = c("confirmed_mon", "deaths_mon")
Gre_month = setnames(Greece[, lapply(.SD, sum), by = .(my = format(as.Date(date), "%b-%y")),.SDcols=select], select, rename)
# Gre_month = Gre_month[order(-confirmed_mon)]
Gre_month$my <- factor(Gre_month$my, levels = Gre_month$my)

p3a = ggplot(Gre_month, aes(x = my, y = confirmed_mon)) +
  geom_point(size = 5) +
  geom_segment(aes(x = my, xend = my, y=0, yend=confirmed_mon)) +
  labs(title="Cases per Month") +
  theme(axis.text.x  = element_text(angle = 90, vjust = 0.5, hjust=1),
        axis.title.y = element_text(margin = margin(r = 20)),
        axis.title.x = element_text(margin = margin(t = 20)))

# Gre_month = Gre_month[order(-deaths_mon)]
Gre_month$my <- factor(Gre_month$my, levels = Gre_month$my)

p3b = ggplot(Gre_month, aes(x = my, y = deaths_mon)) +
  geom_point(size = 5) +
  geom_segment(aes(x = my, xend = my, y=0, yend=deaths_mon)) +
  labs(title="Deaths per Month") +
  theme(axis.text.x  = element_text(angle = 90, vjust = 0.5, hjust=1),
        axis.title.y = element_text(margin = margin(r = 20)),
        axis.title.x = element_text(margin = margin(t = 20)))

ggarrange(p3a, p3b)


# p3_data = ggplot(Gr_month.m, aes(x = month, y=value, fill = variable)) +
  # geom_bar(stat ='identity', position = 'dodge') +
  # theme(axis.text.x = element_text(angle = 90, vjust = 0.5, hjust = 1))
# p3_data

Gr_month <- Greece[, .(conf_monthly = sum(confirmed.ind), death_monthly = sum(deaths.inc)), by = .(month = paste(month(date, label = T), year(date)))]
Gr_month.m <- melt(Gr_month, id.var = 'month') 
Gr_pie_month_conf <- Gr_month.m[variable == "conf_monthly"]
Gr_pie_month_conf <- Gr_pie_month_conf[, percentage := (scales::percent(value / sum(value)))]

Gr_pie_month_conf <- Gr_pie_month_conf[, label := do.call(paste, c(.SD, sep = " : ")), .SDcols = c("month", "percentage")]

p4a <- ggplot(Gr_pie_month_conf, aes(x = "", y = value,  fill = reorder(label, -value))) +
  geom_bar(stat = "identity", color = "black") +
  coord_polar(theta = "y", start = 0) +
  guides(fill=guide_legend(title="Months")) +
  theme_void() + 
  labs(title = "Percentages of confirmed cases in Greece per month")

Gr_pie_month_dead <- Gr_month.m[variable == "death_monthly"]
Gr_pie_month_dead <- Gr_pie_month_dead[, percentage := (scales::percent(value / sum(value)))]

Gr_pie_month_dead <- Gr_pie_month_dead[, label := do.call(paste, c(.SD, sep = " : ")), .SDcols = c("month", "percentage")]

p4b <- ggplot(Gr_pie_month_dead, aes(x = "", y = value,  fill = reorder(label, -value))) +
  geom_bar(stat = "identity", color = "black") +
  coord_polar(theta = "y", start = 0) +
  guides(fill=guide_legend(title="Months")) +
  theme_void() + 
  labs(title = "Percentages of deaths in Greece per month")

ggarrange(p4a, p4b)


#comparative analysis for Greece, Italy, Spain and Portugal per Season
relative <- df_long_merged[Country %in% c("Greece", "Italy", "Spain", "Portugal")]

relative_plot_conf <- ggplot(relative, aes(x = Season, y = confirmed, fill = Country)) +
  geom_bar(position = "dodge", stat = "identity") +
  labs(title = "Relative comparison for confirmed cases in Greece, Italy, Spain and Portugal by Season") +
  theme(axis.text.x = element_text(angle = 60, vjust = 0.5))

death_plot_conf <- ggplot(relative, aes(x = Season, y = deaths, fill = Country)) +
  geom_bar(position = "dodge", stat = "identity") +
  labs(title = "Relative comparison for deaths in Greece, Italy, Spain and Portugal by Season") +
  theme(axis.text.x = element_text(angle = 60, vjust = 0.5))

fatality_plot_conf <- ggplot(relative, aes(x = Season, y = deaths/confirmed, fill = Country)) +
  geom_bar(position = "dodge", stat = "identity") +
  labs(title = "Relative comparison for fatality in Greece, Italy, Spain and Portugal by Season") +
  theme(axis.text.x = element_text(angle = 60, vjust = 0.5))

plot_grid(relative_plot_conf, death_plot_conf, fatality_plot_conf)

suppressMessages(library(rworldmap))
library(countrycode)
library("wpp2019")

#wpp2019 UN Dataset
data(pop) # load population dataset
population = data.table(Country = pop[2], Population = 1000*pop[17])
setnames(population, c('Country.name', 'Population.2020'),c('Country', 'Population'))
population <- population[, code := countrycode(Country, "country.name", "iso3c")]

#latest update Worldwide
latest_update <- select(df_long_merged[which(date == max(date))], Country, confirmed, deaths)
setnames(latest_update, "Country", "region")
latest_update <- latest_update[, code := countrycode(region, "country.name", "iso3c")]

# latest_update <- latest_update %>% mutate(region = ifelse(region == "US", "USA", region)) %>% mutate(region = ifelse(region == "Czechia", "Czech Republic", region))
# latest_update <- latest_update %>% mutate(region = ifelse(region == "Cote d'Ivoire", "Ivory Coast", region))

#data for world_map
world_map <- data.table(map_data("world"))
world_map <- world_map[, code := countrycode(region, "country.name", "iso3c")]

#joining our world_map data with latest update and population per country
world_map <- left_join(latest_update, world_map, by = "code")
world_map <- left_join(world_map, population, by = "code")


world_map$conf_perc <- (world_map$confirmed / world_map$Population)
world_map$dead_perc <- (world_map$deaths / world_map$Population)

#plot for cases, deaths and fatality rate by country (Worldwide)
latest_update <- latest_update[order(-confirmed)]
latest_update$region <- factor(latest_update$region, levels = latest_update$region)

most_conf_plot <- ggplot(latest_update[1:15], aes(x = region, y = confirmed)) +
  geom_bar(stat = "identity", fill = "darkseagreen") + coord_flip() +
  labs(title = "World's most confirmed cases by Country")

latest_update <- latest_update[order(-deaths)]
latest_update$region <- factor(latest_update$region, levels = latest_update$region)

most_deaths_plot <- ggplot(latest_update[1:15], aes(x = region, y = deaths)) +
  geom_bar(stat = "identity", fill = "brown") + coord_flip() +
  labs(title = "World's most deaths by Country")

latest_update <- latest_update[order(-(deaths/confirmed))]
latest_update$region <- factor(latest_update$region, levels = latest_update$region)

greatest_fatality_plot <- ggplot(latest_update[1:15], aes(x = region, y = deaths/confirmed)) +
  geom_bar(stat = "identity", fill = "burlywood4") + coord_flip() +
  labs(title = "World's greatest fatality rate by Country")
plot_grid(most_conf_plot, most_deaths_plot, greatest_fatality_plot)


# ggplot(world_map, aes(long, lat, group = group))+
  geom_polygon(aes(fill = perc ), color = "white") +
  theme(panel.background = element_rect(fill = "lightblue", colour = "lightblue", size = 0.5, linetype = "solid")) +
  # scale_fill_viridis_b(option = "A")
  # scale_fill_gradient(name = "confirmed", high = "#FF0000FF", low = "#FFFF00FF", na.value = "grey50")
  scale_fill_gradient2( low = "blue",
                        mid = "white",
                        high = "red",
                        midpoint = 0.15,
                        space = "Lab",
                        na.value = "grey50",
                        guide = "colourbar",
                        aesthetics = "fill")
  
#Maps to visualize the pandemic 
conf_map <- ggplot(world_map, aes(long, lat, group = group))+
  geom_polygon(aes(fill = 100*conf_perc ), color = "white") +
  theme(panel.background = element_rect(fill = "lightblue", colour = "lightblue", size = 0.5, linetype = "solid")) +
  scale_fill_gradientn(
    colors = c("green", "orange", "red", "blue", "purple", "black"),
    values = NULL,
    space = "Lab",
    na.value = "grey50",
    guide = "colourbar",
    aesthetics = "fill") +
  labs(title = "World map for percentage of confirmed cases by population per Country ")
conf_map

death_map <- ggplot(world_map, aes(long, lat, group = group))+
  geom_polygon(aes(fill = 100*dead_perc ), color = "white") +
  theme(panel.background = element_rect(fill = "lightblue", colour = "lightblue", size = 0.5, linetype = "solid")) +
  scale_fill_gradientn(
    colors = c("green", "orange", "red", "blue", "purple", "black"),
    values = NULL,
    space = "Lab",
    na.value = "grey50",
    guide = "colourbar",
    aesthetics = "fill") +
  labs(title = "World map for percentage of deaths by population per Country ")
death_map

fatality_map <- ggplot(world_map, aes(long, lat, group = group))+
  geom_polygon(aes(fill = deaths / confirmed), color = "white") +
  theme(panel.background = element_rect(fill = "lightblue", colour = "lightblue", size = 0.5, linetype = "solid")) +
  scale_fill_gradientn(
    colors = c("green", "red", "black"),
    values = NULL,
    space = "Lab",
    na.value = "grey50",
    guide = "colourbar",
    aesthetics = "fill") +
  labs(title = "World map for fatality rate per Country ")
fatality_map




