"""
Binance Futures Testnet Trading Bot
Supports market, limit, and stop-limit orders with logging and error handling
"""

import logging
import argparse
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from typing import Dict, Any, Optional
from enum import Enum

from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException, BinanceRequestException


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LIMIT = "STOP_LIMIT"


class TradingBot:
    """Main trading bot class with comprehensive functionality"""
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        """
        Initialize the trading bot
        
        Args:
            api_key: Binance API key
            api_secret: Binance API secret
            testnet: Whether to use testnet (default: True)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        
        # Initialize Binance client
        self.client = Client(
            api_key=self.api_key,
            api_secret=self.api_secret,
            testnet=self.testnet
        )
        
        # Set testnet URL for futures
        if self.testnet:
            self.client.futures_api_url = 'https://testnet.binancefuture.com'
        
        logger.info(f"TradingBot initialized on {'Testnet' if testnet else 'Mainnet'}")
        
    def validate_symbol(self, symbol: str) -> bool:
        """Validate if symbol exists and is tradable"""
        try:
            exchange_info = self.client.futures_exchange_info()
            symbols = [s['symbol'] for s in exchange_info['symbols']]
            return symbol in symbols
        except Exception as e:
            logger.error(f"Error validating symbol {symbol}: {e}")
            return False
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get symbol information including price filters and lot size"""
        try:
            exchange_info = self.client.futures_exchange_info()
            for s in exchange_info['symbols']:
                if s['symbol'] == symbol:
                    return s
        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}: {e}")
        return None
    
    def adjust_quantity(self, symbol: str, quantity: float) -> float:
        """Adjust quantity to match symbol's lot size requirements"""
        try:
            symbol_info = self.get_symbol_info(symbol)
            if not symbol_info:
                return quantity
            
            # Get lot size filter
            for filt in symbol_info['filters']:
                if filt['filterType'] == 'LOT_SIZE':
                    step_size = float(filt['stepSize'])
                    # Round down to nearest step size
                    adjusted_qty = Decimal(str(quantity))
                    step = Decimal(str(step_size))
                    adjusted_qty = (adjusted_qty / step).quantize(Decimal('1.'), rounding=ROUND_DOWN) * step
                    return float(adjusted_qty)
        except Exception as e:
            logger.error(f"Error adjusting quantity: {e}")
        
        return quantity
    
    def adjust_price(self, symbol: str, price: float) -> float:
        """Adjust price to match symbol's tick size requirements"""
        try:
            symbol_info = self.get_symbol_info(symbol)
            if not symbol_info:
                return price
            
            # Get price filter
            for filt in symbol_info['filters']:
                if filt['filterType'] == 'PRICE_FILTER':
                    tick_size = float(filt['tickSize'])
                    # Round to nearest tick size
                    adjusted_price = Decimal(str(price))
                    tick = Decimal(str(tick_size))
                    adjusted_price = (adjusted_price / tick).quantize(Decimal('1.'), rounding=ROUND_DOWN) * tick
                    return float(adjusted_price)
        except Exception as e:
            logger.error(f"Error adjusting price: {e}")
        
        return price
    
    def get_account_balance(self) -> Dict[str, float]:
        """Get account balance"""
        try:
            account = self.client.futures_account()
            assets = {}
            for asset in account['assets']:
                if float(asset['walletBalance']) > 0:
                    assets[asset['asset']] = {
                        'wallet_balance': float(asset['walletBalance']),
                        'available_balance': float(asset['availableBalance'])
                    }
            return assets
        except Exception as e:
            logger.error(f"Error getting account balance: {e}")
            return {}
    
    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current position for a symbol"""
        try:
            positions = self.client.futures_position_information()
            for position in positions:
                if position['symbol'] == symbol and float(position['positionAmt']) != 0:
                    return {
                        'symbol': position['symbol'],
                        'position_amt': float(position['positionAmt']),
                        'entry_price': float(position['entryPrice']),
                        'unrealized_pnl': float(position['unRealizedProfit'])
                    }
            return None
        except Exception as e:
            logger.error(f"Error getting position for {symbol}: {e}")
            return None
    
    def place_market_order(
        self, 
        symbol: str, 
        side: str, 
        quantity: float,
        reduce_only: bool = False
    ) -> Dict[str, Any]:
        """
        Place a market order
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            side: 'BUY' or 'SELL'
            quantity: Order quantity
            reduce_only: Whether order should only reduce position
            
        Returns:
            Order response dictionary
        """
        try:
            # Validate inputs
            if side.upper() not in ['BUY', 'SELL']:
                raise ValueError("Side must be either 'BUY' or 'SELL'")
            
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
            
            if not self.validate_symbol(symbol):
                raise ValueError(f"Invalid symbol: {symbol}")
            
            # Adjust quantity
            adjusted_qty = self.adjust_quantity(symbol, quantity)
            
            logger.info(f"Placing market order: {symbol} {side} {adjusted_qty}")
            
            # Place order
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side.upper(),
                type='MARKET',
                quantity=adjusted_qty,
                reduceOnly=reduce_only
            )
            
            logger.info(f"Market order placed successfully: {order}")
            return order
            
        except (BinanceAPIException, BinanceOrderException, BinanceRequestException) as e:
            logger.error(f"Binance API error placing market order: {e}")
            raise
        except Exception as e:
            logger.error(f"Error placing market order: {e}")
            raise
    
    def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        time_in_force: str = 'GTC',
        reduce_only: bool = False
    ) -> Dict[str, Any]:
        """
        Place a limit order
        
        Args:
            symbol: Trading pair
            side: 'BUY' or 'SELL'
            quantity: Order quantity
            price: Limit price
            time_in_force: 'GTC', 'IOC', or 'FOK'
            reduce_only: Whether order should only reduce position
            
        Returns:
            Order response dictionary
        """
        try:
            # Validate inputs
            if side.upper() not in ['BUY', 'SELL']:
                raise ValueError("Side must be either 'BUY' or 'SELL'")
            
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
            
            if price <= 0:
                raise ValueError("Price must be positive")
            
            if time_in_force not in ['GTC', 'IOC', 'FOK']:
                raise ValueError("Time in force must be 'GTC', 'IOC', or 'FOK'")
            
            if not self.validate_symbol(symbol):
                raise ValueError(f"Invalid symbol: {symbol}")
            
            # Adjust quantity and price
            adjusted_qty = self.adjust_quantity(symbol, quantity)
            adjusted_price = self.adjust_price(symbol, price)
            
            logger.info(f"Placing limit order: {symbol} {side} {adjusted_qty} @ {adjusted_price}")
            
            # Place order
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side.upper(),
                type='LIMIT',
                quantity=adjusted_qty,
                price=adjusted_price,
                timeInForce=time_in_force,
                reduceOnly=reduce_only
            )
            
            logger.info(f"Limit order placed successfully: {order}")
            return order
            
        except (BinanceAPIException, BinanceOrderException, BinanceRequestException) as e:
            logger.error(f"Binance API error placing limit order: {e}")
            raise
        except Exception as e:
            logger.error(f"Error placing limit order: {e}")
            raise
    
    def place_stop_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        stop_price: float,
        time_in_force: str = 'GTC',
        reduce_only: bool = False
    ) -> Dict[str, Any]:
        """
        Place a stop-limit order
        
        Args:
            symbol: Trading pair
            side: 'BUY' or 'SELL'
            quantity: Order quantity
            price: Limit price
            stop_price: Stop price to trigger the order
            time_in_force: 'GTC', 'IOC', or 'FOK'
            reduce_only: Whether order should only reduce position
            
        Returns:
            Order response dictionary
        """
        try:
            # Validate inputs
            if side.upper() not in ['BUY', 'SELL']:
                raise ValueError("Side must be either 'BUY' or 'SELL'")
            
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
            
            if price <= 0:
                raise ValueError("Price must be positive")
            
            if stop_price <= 0:
                raise ValueError("Stop price must be positive")
            
            if time_in_force not in ['GTC', 'IOC', 'FOK']:
                raise ValueError("Time in force must be 'GTC', 'IOC', or 'FOK'")
            
            if not self.validate_symbol(symbol):
                raise ValueError(f"Invalid symbol: {symbol}")
            
            # Adjust values
            adjusted_qty = self.adjust_quantity(symbol, quantity)
            adjusted_price = self.adjust_price(symbol, price)
            adjusted_stop_price = self.adjust_price(symbol, stop_price)
            
            logger.info(f"Placing stop-limit order: {symbol} {side} {adjusted_qty} @ {adjusted_price} (stop: {adjusted_stop_price})")
            
            # Place order
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side.upper(),
                type='STOP',
                quantity=adjusted_qty,
                price=adjusted_price,
                stopPrice=adjusted_stop_price,
                timeInForce=time_in_force,
                reduceOnly=reduce_only
            )
            
            logger.info(f"Stop-limit order placed successfully: {order}")
            return order
            
        except (BinanceAPIException, BinanceOrderException, BinanceRequestException) as e:
            logger.error(f"Binance API error placing stop-limit order: {e}")
            raise
        except Exception as e:
            logger.error(f"Error placing stop-limit order: {e}")
            raise
    
    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Cancel an existing order"""
        try:
            logger.info(f"Cancelling order {order_id} for {symbol}")
            result = self.client.futures_cancel_order(
                symbol=symbol,
                orderId=order_id
            )
            logger.info(f"Order cancelled successfully: {result}")
            return result
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            raise
    
    def get_order_status(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Get order status"""
        try:
            order = self.client.futures_get_order(
                symbol=symbol,
                orderId=order_id
            )
            return order
        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            raise
    
    def get_open_orders(self, symbol: Optional[str] = None) -> list:
        """Get all open orders"""
        try:
            if symbol:
                orders = self.client.futures_get_open_orders(symbol=symbol)
            else:
                orders = self.client.futures_get_open_orders()
            return orders
        except Exception as e:
            logger.error(f"Error getting open orders: {e}")
            raise
    
    def close_all_positions(self, symbol: Optional[str] = None):
        """Close all positions"""
        try:
            positions = self.client.futures_position_information()
            
            for position in positions:
                if symbol and position['symbol'] != symbol:
                    continue
                
                position_amt = float(position['positionAmt'])
                if position_amt != 0:
                    close_side = 'SELL' if position_amt > 0 else 'BUY'
                    close_qty = abs(position_amt)
                    
                    try:
                        self.place_market_order(
                            symbol=position['symbol'],
                            side=close_side,
                            quantity=close_qty,
                            reduce_only=True
                        )
                        logger.info(f"Closed position for {position['symbol']}: {close_qty} @ {close_side}")
                    except Exception as e:
                        logger.error(f"Error closing position for {position['symbol']}: {e}")
                        
        except Exception as e:
            logger.error(f"Error in close_all_positions: {e}")
            raise


class CommandLineInterface:
    """Command-line interface for the trading bot"""
    
    def __init__(self):
        self.bot = None
        
    def initialize_bot(self):
        """Initialize the trading bot with user credentials"""
        print("=" * 50)
        print("Binance Futures Testnet Trading Bot")
        print("=" * 50)
        
        # Get API credentials
        api_key = input("Enter your Binance Testnet API Key: ").strip()
        api_secret = input("Enter your Binance Testnet API Secret: ").strip()
        
        try:
            self.bot = TradingBot(api_key, api_secret, testnet=True)
            print("✓ Bot initialized successfully!")
            
            # Show account balance
            balance = self.bot.get_account_balance()
            if balance:
                print("\nAccount Balance:")
                for asset, info in balance.items():
                    print(f"  {asset}: {info['available_balance']} (available)")
            else:
                print("No balance information available")
                
        except Exception as e:
            print(f"✗ Error initializing bot: {e}")
            return False
        
        return True
    
    def main_menu(self):
        """Display main menu"""
        while True:
            print("\n" + "=" * 50)
            print("MAIN MENU")
            print("=" * 50)
            print("1. Place Market Order")
            print("2. Place Limit Order")
            print("3. Place Stop-Limit Order")
            print("4. Check Order Status")
            print("5. Cancel Order")
            print("6. View Open Orders")
            print("7. View Account Balance")
            print("8. View Position")
            print("9. Close All Positions")
            print("0. Exit")
            
            choice = input("\nSelect an option (0-9): ").strip()
            
            if choice == '0':
                print("Exiting... Goodbye!")
                break
            elif choice == '1':
                self.place_order_menu(OrderType.MARKET)
            elif choice == '2':
                self.place_order_menu(OrderType.LIMIT)
            elif choice == '3':
                self.place_order_menu(OrderType.STOP_LIMIT)
            elif choice == '4':
                self.check_order_status_menu()
            elif choice == '5':
                self.cancel_order_menu()
            elif choice == '6':
                self.view_open_orders_menu()
            elif choice == '7':
                self.view_balance()
            elif choice == '8':
                self.view_position_menu()
            elif choice == '9':
                self.close_positions_menu()
            else:
                print("Invalid choice. Please try again.")
    
    def place_order_menu(self, order_type: OrderType):
        """Place order menu"""
        print(f"\nPlace {order_type.value} Order")
        print("-" * 30)
        
        symbol = input("Symbol (e.g., BTCUSDT, ETHUSDT): ").strip().upper()
        
        # Validate symbol
        if not self.bot.validate_symbol(symbol):
            print(f"✗ Invalid symbol: {symbol}")
            return
        
        side = input("Side (BUY/SELL): ").strip().upper()
        if side not in ['BUY', 'SELL']:
            print("✗ Invalid side. Must be BUY or SELL")
            return
        
        quantity = float(input("Quantity: ").strip())
        
        price = None
        stop_price = None
        
        if order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT]:
            price = float(input("Price: ").strip())
        
        if order_type == OrderType.STOP_LIMIT:
            stop_price = float(input("Stop Price: ").strip())
        
        reduce_only_input = input("Reduce Only? (y/N): ").strip().lower()
        reduce_only = reduce_only_input == 'y'
        
        try:
            if order_type == OrderType.MARKET:
                result = self.bot.place_market_order(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    reduce_only=reduce_only
                )
            elif order_type == OrderType.LIMIT:
                result = self.bot.place_limit_order(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=price,
                    reduce_only=reduce_only
                )
            elif order_type == OrderType.STOP_LIMIT:
                result = self.bot.place_stop_limit_order(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=price,
                    stop_price=stop_price,
                    reduce_only=reduce_only
                )
            
            print(f"\n✓ Order placed successfully!")
            print(f"Order ID: {result['orderId']}")
            print(f"Status: {result['status']}")
            
        except Exception as e:
            print(f"✗ Error placing order: {e}")
    
    def check_order_status_menu(self):
        """Check order status menu"""
        print("\nCheck Order Status")
        print("-" * 30)
        
        symbol = input("Symbol: ").strip().upper()
        order_id = int(input("Order ID: ").strip())
        
        try:
            status = self.bot.get_order_status(symbol, order_id)
            print(f"\nOrder Status:")
            print(f"ID: {status['orderId']}")
            print(f"Symbol: {status['symbol']}")
            print(f"Side: {status['side']}")
            print(f"Type: {status['type']}")
            print(f"Status: {status['status']}")
            print(f"Price: {status['price']}")
            print(f"Quantity: {status['origQty']}")
            print(f"Filled: {status['executedQty']}")
        except Exception as e:
            print(f"✗ Error checking order status: {e}")
    
    def cancel_order_menu(self):
        """Cancel order menu"""
        print("\nCancel Order")
        print("-" * 30)
        
        symbol = input("Symbol: ").strip().upper()
        order_id = int(input("Order ID: ").strip())
        
        confirm = input(f"Are you sure you want to cancel order {order_id}? (y/N): ").strip().lower()
        if confirm != 'y':
            print("Cancellation aborted")
            return
        
        try:
            result = self.bot.cancel_order(symbol, order_id)
            print(f"✓ Order {order_id} cancelled successfully")
        except Exception as e:
            print(f"✗ Error cancelling order: {e}")
    
    def view_open_orders_menu(self):
        """View open orders menu"""
        print("\nOpen Orders")
        print("-" * 30)
        
        symbol = input("Symbol (leave empty for all): ").strip().upper()
        
        try:
            orders = self.bot.get_open_orders(symbol if symbol else None)
            
            if not orders:
                print("No open orders")
                return
            
            for order in orders:
                print(f"\nOrder ID: {order['orderId']}")
                print(f"Symbol: {order['symbol']}")
                print(f"Side: {order['side']}")
                print(f"Type: {order['type']}")
                print(f"Price: {order['price']}")
                print(f"Quantity: {order['origQty']}")
                print(f"Filled: {order['executedQty']}")
                print(f"Status: {order['status']}")
                print("-" * 20)
                
        except Exception as e:
            print(f"✗ Error fetching open orders: {e}")
    
    def view_balance(self):
        """View account balance"""
        print("\nAccount Balance")
        print("-" * 30)
        
        try:
            balance = self.bot.get_account_balance()
            if not balance:
                print("No balance information available")
                return
            
            total_value = 0
            for asset, info in balance.items():
                value = info['available_balance']
                total_value += value
                print(f"{asset}: {value:.4f} (available)")
            
            print(f"\nTotal Available Balance: {total_value:.4f} USDT")
            
        except Exception as e:
            print(f"✗ Error fetching balance: {e}")
    
    def view_position_menu(self):
        """View position menu"""
        print("\nView Position")
        print("-" * 30)
        
        symbol = input("Symbol: ").strip().upper()
        
        try:
            position = self.bot.get_position(symbol)
            if position:
                print(f"\nPosition for {symbol}:")
                print(f"Amount: {position['position_amt']}")
                print(f"Entry Price: {position['entry_price']}")
                print(f"Unrealized PnL: {position['unrealized_pnl']}")
            else:
                print(f"No position found for {symbol}")
                
        except Exception as e:
            print(f"✗ Error fetching position: {e}")
    
    def close_positions_menu(self):
        """Close positions menu"""
        print("\nClose Positions")
        print("-" * 30)
        
        symbol = input("Symbol (leave empty for all): ").strip().upper()
        
        confirm = input(f"Are you sure you want to close {'all' if not symbol else symbol} positions? (y/N): ").strip().lower()
        if confirm != 'y':
            print("Operation cancelled")
            return
        
        try:
            if symbol:
                self.bot.close_all_positions(symbol)
                print(f"✓ Closed all positions for {symbol}")
            else:
                self.bot.close_all_positions()
                print("✓ Closed all positions")
                
        except Exception as e:
            print(f"✗ Error closing positions: {e}")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Binance Futures Trading Bot')
    
    parser.add_argument(
        '--api-key',
        help='Binance API Key (optional, will prompt if not provided)'
    )
    
    parser.add_argument(
        '--api-secret',
        help='Binance API Secret (optional, will prompt if not provided)'
    )
    
    parser.add_argument(
        '--symbol',
        help='Trading symbol (e.g., BTCUSDT)'
    )
    
    parser.add_argument(
        '--side',
        choices=['BUY', 'SELL'],
        help='Order side'
    )
    
    parser.add_argument(
        '--type',
        choices=['MARKET', 'LIMIT', 'STOP_LIMIT'],
        help='Order type'
    )
    
    parser.add_argument(
        '--quantity',
        type=float,
        help='Order quantity'
    )
    
    parser.add_argument(
        '--price',
        type=float,
        help='Order price (for limit/stop-limit orders)'
    )
    
    parser.add_argument(
        '--stop-price',
        type=float,
        help='Stop price (for stop-limit orders)'
    )
    
    parser.add_argument(
        '--balance',
        action='store_true',
        help='Show account balance'
    )
    
    parser.add_argument(
        '--open-orders',
        action='store_true',
        help='Show open orders'
    )
    
    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_arguments()
    
    if any([args.symbol, args.side, args.type, args.quantity]):
        # CLI mode
        try:
            if not args.api_key or not args.api_secret:
                print("Error: API key and secret are required for CLI mode")
                return
            
            bot = TradingBot(args.api_key, args.api_secret, testnet=True)
            
            if args.balance:
                balance = bot.get_account_balance()
                print("Account Balance:")
                for asset, info in balance.items():
                    print(f"{asset}: {info['available_balance']}")
            
            elif args.open_orders:
                orders = bot.get_open_orders()
                print("Open Orders:")
                for order in orders:
                    print(f"{order['symbol']} - {order['side']} {order['origQty']} @ {order['price']}")
            
            elif all([args.symbol, args.side, args.type, args.quantity]):
                if args.type == 'MARKET':
                    result = bot.place_market_order(
                        symbol=args.symbol,
                        side=args.side,
                        quantity=args.quantity
                    )
                elif args.type == 'LIMIT' and args.price:
                    result = bot.place_limit_order(
                        symbol=args.symbol,
                        side=args.side,
                        quantity=args.quantity,
                        price=args.price
                    )
                elif args.type == 'STOP_LIMIT' and args.price and args.stop_price:
                    result = bot.place_stop_limit_order(
                        symbol=args.symbol,
                        side=args.side,
                        quantity=args.quantity,
                        price=args.price,
                        stop_price=args.stop_price
                    )
                else:
                    print("Error: Missing required arguments for order type")
                    return
                
                print(f"Order placed successfully: {result}")
            
            else:
                print("Error: Missing required arguments for order placement")
        
        except Exception as e:
            print(f"Error: {e}")
    
    else:
        # Interactive mode
        cli = CommandLineInterface()
        if cli.initialize_bot():
            cli.main_menu()


if __name__ == "__main__":
    main()
